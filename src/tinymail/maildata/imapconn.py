import imaplib
import email
import re

list_pattern = re.compile(r'^\((?P<flags>[^\)]*)\) '
                          r'"(?P<delim>[^"]*)" '
                          r'(?P<name>.*)$')

class ImapServerConnection(object):
    def __init__(self, host, login_name, login_pass):
        self.conn = imaplib.IMAP4_SSL(host)
        #print "connected"
        #print self.conn.capabilities
        self.conn.login(login_name, login_pass)
        #print "logged in"

    def get_mailboxes(self):
        status, entries = self.conn.list()
        assert status == 'OK'

        for entry in entries:
            m = list_pattern.match(entry)
            assert m is not None
            folder_path = m.group('name').strip('"')
            yield folder_path

    def get_messages_in_mailbox(self, mbox_name):
        status, count = self.conn.select(mbox_name, readonly=True)
        assert status == 'OK'

        status, data = self.conn.search(None, 'All')
        assert status == 'OK'
        message_ids = data[0].split()

        # we need to get FLAGS too, otherwise messages are marked as read
        status, data = self.conn.fetch(','.join(message_ids),
                                       '(BODY.PEEK[HEADER] FLAGS)')
        assert status == 'OK'
        data = iter(data)
        while True:
            fragment = next(data)
            assert len(fragment) == 2, 'unexpected fragment layout'
            preamble, headers = fragment
            assert 'BODY[HEADER]' in preamble, 'bad preamble'

            yield email.message_from_string(headers)

            closing = next(data, None)
            assert closing == ')', 'bad closing'

    def cleanup(self):
        self.conn.shutdown()
        print "finished"
