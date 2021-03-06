import functools
from thread import get_ident as current_thread
import threading
import Queue

from Foundation import objc, NSObject, NSAutoreleasePool

from imapserver import get_imap_loop

class MainThreadHelper(NSObject):
    def onMainThread(self):
        self.func()

def main_thread(func, *args, **kwargs):
    """ Schedue `func` to be called on the main thread. """

    pool = NSAutoreleasePool.new()

    obj = MainThreadHelper.new()
    obj.func = lambda: func(*args, **kwargs)

    selector = objc.selector(obj.onMainThread, signature='v@:')
    later = obj.performSelectorOnMainThread_withObject_waitUntilDone_
    later(selector, None, False)


_main_thread_id = current_thread()

def assert_main_thread(f):
    """ Make sure the wrapped function is called on the main thread. """

    msg = "%r must be run on main thread" % f

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        assert current_thread() == _main_thread_id, msg
        return f(*args, **kwargs)

    return wrapper

def connect_to_server(reg, config):
    run_loop = get_imap_loop(config)
    in_queue = Queue.Queue()
    thread = threading.Thread(target=run_loop, args=(in_queue,))
    thread.start()

    def quit():
        in_queue.put(None)
        thread.join()

    def remote_do(op):
        op.is_queued(reg)
        in_queue.put(op)

    return remote_do, quit

class MailDataOp(object):
    """ Base class for potentially-long-running operations. """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.state_msg = 'queued'

    def is_queued(self, reg):
        self.reg = reg
        self.reg.notify('maildata.op_queued', op=self)
        self.state_update('queued')

    @assert_main_thread
    def state_update(self, msg):
        self.state_msg = msg
        self.reg.notify('maildata.op_status', op=self)

    @assert_main_thread
    def report_on_main(self, result):
        self.state_update('reporting')
        self.report(result)
        self.state_update('done')
        self.reg.notify('maildata.op_finished', op=self)

    def __call__(self, imap):
        """ To be called by IMAP connection thread """
        main_thread(self.state_update, 'working')
        result = self.perform(imap)
        main_thread(self.report_on_main, result)

    def perform(self, imap):
        """
        Subclasses must implement this method to do their work. It's
        called in a worker thread. Should return a single `result` object.
        """
        raise NotImplementedError

    def report(self, result):
        """
        Subclasses must implement this method to report their result
        back to objects on the main thread. Receives one `result` object
        (the one returned by `perform`) as parameter.
        """
        raise NotImplementedError
