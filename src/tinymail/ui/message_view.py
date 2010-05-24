from Foundation import NSObject, NSURL, NSString, NSISOLatin1StringEncoding

class MessageView(NSObject):
    def attach_to_view(self, web_view):
        self.web_view = web_view

    def show_message(self, mime_message):
        if mime_message is None:
            str_data = ""
        else:
            str_data = mime_message.as_string()

        ns_str = NSString.stringWithString_(str_data.decode('latin-1'))
        data = ns_str.dataUsingEncoding_(NSISOLatin1StringEncoding)
        url = NSURL.URLWithString_('about:blank')
        self.web_view.mainFrame().loadData_MIMEType_textEncodingName_baseURL_(
                    data, 'text/plain', 'latin-1', url)
