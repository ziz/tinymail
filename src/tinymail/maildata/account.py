from async import assert_main_thread, connect_to_server, MailDataOp
from folder import Folder


class Account(object):
    def __init__(self, reg, config):
        self.reg = reg
        self.folders = []
        self._needs_update = True
        self._configure(config)

    def _configure(self, config):
        remote = connect_to_server(self.reg, config)
        (self.remote_do, self.remote_cleanup) = remote

    def update_if_needed(self):
        if self._needs_update:
            self._needs_update = False
            self.remote_do(ListFoldersOp(account=self))

    @assert_main_thread
    def _imap_folder_list_loaded(self, imap_folders):
        self.folders[:] = [Folder(self, imap_name)
                           for imap_name in imap_folders]
        self.reg.notify((self, 'folders_updated'), account=self)

    def cleanup(self):
        self.remote_cleanup()

class ListFoldersOp(MailDataOp):
    def perform(self, imap):
        return imap.get_mailboxes()

    def report(self, result):
        self.account._imap_folder_list_loaded(result)
