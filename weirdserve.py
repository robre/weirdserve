#!/usr/bin/env python
# weirdserve.py ~ an odd webserver
# @author: Robert Reith (@_robre)
# @license: ...
# 

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import threading
import sys
import random
enc = 'UTF-8'
config = {
    "fuzz_headers": False,  # Fuzz HTTP Headers
    "fuzz_body": True,  # Fuzz HTTP Body
    "fuzz_protocol_version": True,  # Fuzz HTTP Protocol Version
    "fuzz_header_content_type": True,
    "fuzz_header_content_length": True,
    "fuzz_header_server": True,
    "fuzz_response_value": True,
}
fuzzy_vals = {
    "string": ["", "null", "'", ";|<>()", "\n\t\x00"],
    "int": [0, 1, -1, sys.maxsize, 0xff, 0xffff, 0xefff]
}

class RequestHandler(BaseHTTPRequestHandler):
    def version_string(self):
        if config["fuzz_header_server"]:
            server_version = random.choice(fuzzy_vals["string"])
            return server_version
        else:
            return "Test/1.0"
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        print("s--------------------------")
        print(self.path)
        print(self.client_address)
        print(self.command)
        print(self.request_version)
        print(self.headers)
        print(params)
        print("e--------------------------")
        if config["fuzz_protocol_version"]:
            self.protocol_version = random.choice(
                fuzzy_vals["string"] + ["HTTP/0.9", "HTTP/1.0", 
                                       "HTTP/1.1", "HTTP/1.2",
                                       "HTTP/2.0", "HTTP/0.0",
                                       "HTTP/13.37"])


        if config["fuzz_response_value"]:
            self.send_response(random.choice(
                fuzzy_vals["int"] + list(range(200,204)) + list(range(400,406)) + list(range(500,600)) + [random.randint(0,10000)]
            ))
        else:
            self.send_response(200)
        if config["fuzz_header_content_type"]:
            self.send_header('Content-type', random.choice(fuzzy_vals["string"] + ["text/html", "application/javascript", "application/octet-stream", "asd/dlak"]))
        else:
            self.send_header('Content-type','text/html')
        #if config["fuzz_header_server"]:
        #    self.server_version = "YO"
        #    self.send_header('Server', random.choice(fuzzy_vals["string"]))
        self.end_headers()
        if config["fuzz_body"]:
            message = random.choice(fuzzy_vals["string"])
        else:
            message = ""

        self.wfile.write(bytes(message, enc))
        return

    def send_header(self, keyword, value):
        """Send a MIME header to the headers buffer."""
        print("[*] send_header")
        if self.request_version != 'HTTP/0.9':
            if not hasattr(self, '_headers_buffer'):
                self._headers_buffer = []
            self._headers_buffer.append(
                ("%s: %s\r\n" % (keyword, value)).encode('latin-1', 'strict'))

        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.close_connection = True
            elif value.lower() == 'keep-alive':
                self.close_connection = False

    def send_head(self):
        """Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        print("[*] send_head")
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        # check for trailing "/" which should return 404. See Issue17324
        # The test for this was added in test_httpserver.py
        # However, some OS platforms accept a trailingSlash as a filename
        # See discussion on python-dev and Issue34711 regarding
        # parseing and rejection of filenames with a trailing slash
        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            # Use browser cache if possible
            if ("If-Modified-Since" in self.headers
                    and "If-None-Match" not in self.headers):
                # compare If-Modified-Since and time of last file modification
                try:
                    ims = email.utils.parsedate_to_datetime(
                        self.headers["If-Modified-Since"])
                except (TypeError, IndexError, OverflowError, ValueError):
                    # ignore ill-formed values
                    pass
                else:
                    if ims.tzinfo is None:
                        # obsolete format with no timezone, cf.
                        # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                        ims = ims.replace(tzinfo=datetime.timezone.utc)
                    if ims.tzinfo is datetime.timezone.utc:
                        # compare to UTC datetime of last modification
                        last_modif = datetime.datetime.fromtimestamp(
                            fs.st_mtime, datetime.timezone.utc)
                        # remove microseconds, like in If-Modified-Since
                        last_modif = last_modif.replace(microsecond=0)

                        if last_modif <= ims:
                            self.send_response(HTTPStatus.NOT_MODIFIED)
                            self.end_headers()
                            f.close()
                            return None

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified",
                self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise


def main():
    server_address=('0.0.0.0', 3337)
    httpd = HTTPServer(server_address, RequestHandler)
    #t = threading.Thread(name='server', target=httpd.serve_forever())
    #t.start()
    while True:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("exiting")
            sys.exit()

if __name__ == "__main__":
    main()
