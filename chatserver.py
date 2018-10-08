# -----------------------------------------------------------------------------
#
# Copyright (c) 1986-2018 Pixar. All rights reserved.
#
# The information in this file (the "Software") is provided for the exclusive
# use of the software licensees of Pixar ("Licensees").  Licensees have the
# right to incorporate the Software into other products for use by other
# authorized software licensees of Pixar, without fee. Except as expressly
# permitted herein, the Software may not be disclosed to third parties, copied
# or duplicated in any form, in whole or in part, without the prior written
# permission of Pixar.
#
# The copyright notices in the Software and this entire statement, including the
# above license grant, this restriction and the following disclaimer, must be
# included in all copies of the Software, in whole or in part, and all permitted
# derivative works of the Software, unless such copies or derivative works are
# solely in the form of machine-executable object code generated by a source
# language processor.
#
# PIXAR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL PIXAR BE
# LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION
# OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.  IN NO CASE WILL
# PIXAR'S TOTAL LIABILITY FOR ALL DAMAGES ARISING OUT OF OR IN CONNECTION WITH
# THE USE OR PERFORMANCE OF THIS SOFTWARE EXCEED $50.
#
# Pixar
# 1200 Park Ave
# Emeryville CA 94608
#
# -----------------------------------------------------------------------------

import socketserver
import threading
import re


class CmdString(object):
    """Class for holding "well ordered" commands of the form:
        cmd -opt1 <value> -opt2 <value2> [;]

        where there opt and values are always in pairs and value
        can be quoted with either {}'s or ""'s in which case the
        value can contain spaces, newlines. " and } can appear in
        value if preceded by \
    """

    def __init__(self, s):

        #
        s = s.decode()
        self.cmd, sep, opts = s.partition(' ')
        if opts.endswith(';'):
            opts = opts[:-1]

        # parse out strings like:
        #  dspyParam -proto {it} -user {j\nb} -foo bar -baz "James Brown"'
        pat_flag = re.compile(r'\s*-(\w+)')

        #
        # get a string inside {}'s but allow nesting of {}'s by supporting
        # \} to escape the end of a block (?: is a non-capturing group and
        # (?<=\\) is a look-behind assertion, in this case preceded
        # by a \.
        pat_curly = re.compile(r'\s*{((?:(?<=\\)}|[^}])*)}')

        # like curly but start and end with double quotes
        pat_dquotes = re.compile(r'\s*"((?:(?<=\\)"|[^"])*)"')

        pat_word = re.compile(r'\s*([^-\s][^\s]*)')

        cflag = None
        self.args = list()
        self.dargs = dict()

        # walk the string, alternate between flags and values, slicing
        # off what we've parsed so far

        while len(opts) > 0:

            # 1. flags
            m = pat_flag.match(opts)
            if not m:
                return
            cflag = m.groups()[0]
            self.args.append(cflag)
            if cflag not in self.dargs:
                self.dargs[cflag] = None

            opts = opts[len(m.group()):]

            # 2. values
            while m:
                m = pat_curly.match(opts)
                if m:
                    curly = m.groups()[0]
                    curly = curly.replace('\\}', '}')
                    self.addValue(cflag, curly)
                    opts = opts[len(m.group()):]
                    continue

                m = pat_dquotes.match(opts)
                if m:
                    dquotes = m.groups()[0]
                    dquotes = dquotes.replace('\\"', '"')
                    self.addValue(cflag, dquotes)
                    opts = opts[len(m.group()):]
                    continue

                m = pat_word.match(opts)
                if m:
                    word = m.groups()[0]
                    self.addValue(cflag, word)
                    opts = opts[len(m.group()):]
                    continue

    def addValue(self, flag, value):
        self.args.append(value)
        if not flag:
            return
        if flag in self.dargs and self.dargs[flag] is not None:
            self.dargs[flag] = self.dargs[flag] + ' ' + value
        else:
            self.dargs[flag] = value

    def getCommand(self):
        return self.cmd

    def getOpt(self, flag, defaultValue=None):
        if flag in self.dargs:
            return self.dargs[flag]
        elif defaultValue is not None:
            return defaultValue
        return None


class ItBaseHandler:
    """A protocol handler, sub-classes are expected to override dspyRender
    taking care that this method will run in it's own thread."""

    def __init__(self, request):
        self.request = request

    def handle(self):
        while True:
            data = self.request.recv(2048).strip()
            if data == '':
                break
            ack = "ok\x00"
            self.request.sendall(ack.encode())
            data = data[:-1]  # remove the trailing nul
            self.msg = CmdString(data)
            cmd = self.msg.getCommand()
            if cmd == 'dspyRender':
                self.dspyRender()
            elif cmd == 'dspyIPR':
                self.dspyIPR()
            elif cmd == 'stopRender':
                self.stopRender()
            elif cmd == 'SelectObject':
                self.selectObjectById()
            elif cmd == 'SelectSurface':
                self.selectSurfaceById()
            else:
                pass

    def dspyRender(self):
        """Overriders should look in self.cmd for the arguments to dspyRender"""
        pass

    def dspyIPR(self):
        pass

    def stopRender(self):
        pass

    def selectObjectById(self):
        pass

    def selectSurfaceById(self):
        pass


protocols = {
    'it': ItBaseHandler,
}


class CommandHandler(socketserver.ThreadingMixIn, socketserver.BaseRequestHandler):
    """
    The request handler.
    """

    def handle(self):

        self.data = self.request.recv(1024).strip()
        ack = "ok\x00"
        self.request.sendall(ack.encode())

        protocol = self.digestProtocol(self.data)
        if protocol:
            handler = protocol(self.request)
            handler.handle()

    def digestProtocol(self, connectString):

        header = CmdString(connectString)
        magic = header.getCommand()
        if magic != 'UtTcpOpen':
            return None

        try:
            pname = header.getOpt("proto")
            handler = protocols[pname]
            return handler
        except ValueError:
            return None


if __name__ == "__main__":
    import time
    print("hello")
    s = 'dspyParams -proto {it} -user {j\nb} -foo bar -crop 0.0 1 0.0 1.0 -baz "James Brown"'
    cs = CmdString(s)
    cmd = cs.getCommand()
    proto = cs.getOpt('proto')
    user = cs.getOpt('user')
    foo = cs.getOpt('foo')
    crop = cs.getOpt('crop')
    baz = cs.getOpt('baz')

    # zero port makes the OS pick one
    host, port = "localhost", 0

    # Create the server, binding to localhost on port 9999
    server = socketserver.TCPServer((host, port), CommandHandler)
    ip, port = server.server_address

    print("serving on port %s port = %d" % (str(ip), port))

    thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    thread.daemon = True
    thread.start()

    print("now serving")

    while True:
        time.sleep(2)
        print("tick")
