# -----------------------------------------------------------------------------
#
# Copyright (c) 1986-2019 Pixar. All rights reserved.
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

import os
import os.path
import sys


class FilePath(str):
    """A class based on unicode to handle filepaths on various OS platforms.

    Extends:
        unicode
    """

    def __new__(cls, path):
        """Create new unicode file path in POSIX format. Windows paths will be
        converted to forward slashes.

        Arguments:
            path {str} -- a file path, in any format.
        """
        if not isinstance(path, str):
            # make sure we use python's native encoding
            # err =  'NEW: %r\n' % path
            for codec in [sys.getfilesystemencoding(), sys.getdefaultencoding()]:
                try:
                    # some unknown encoding to python native encoding
                    fpath = str(path.decode(codec))
                except (UnicodeDecodeError, UnicodeEncodeError) as err:
                    # err += '  |_ CAN NOT DECODE as %s: %r\n' % (codec, path)
                    # err += '     |_ %s\n' % err
                    continue
                else:
                    # err += '  |_ decoded as %s: %s (%r)' % (codec, fpath, fpath)
                    # err = ''
                    break
            # if err:
            #     print err
        else:
            fpath = path
        if os.sep != '/':
            fpath = fpath.replace('\\', '/')
        return str.__new__(cls, fpath)

    def os_path(self):
        """return the platform-specif path, i.e. convert to windows format if
        need be.

        Returns:
            str -- a path formatted for the current OS.
        """
        return str(os.path.normpath(self))

    def exists(self):
        """Check is the path actually exists, using os.path.

        Returns:
            bool -- True if the path exists.
        """
        return os.path.exists(self)

    def join(self, *args):
        """Combine the arguments with the current path and return a new
        FilePath object.

        Arguments:
            *args {list} -- a list of path segments.

        Returns:
            FilePath -- A new object containing the joined path.
        """
        return FilePath(os.path.join(self, *args))

    def dirname(self):
        """Returns the dirname of the current path (using os.path.dirname) as a
        FilePath object.

        Returns:
            FilePath -- the path's directory name.
        """
        return FilePath(os.path.dirname(self))

    def basename(self):
        """Return the basename, i.e. '/path/to/file.ext' -> 'file.ext'

        Returns:
            str -- The final segment of the path.
        """
        return os.path.basename(self)

    def is_writable(self):
        """Checks if the path is writable. The Write and Execute bits must
        be enabled.

        Returns:
            bool -- True is writable
        """
        return os.access(self, os.W_OK | os.X_OK)

    def expandvars(self):
        """Return a Filepath with expanded environment variables and '~'.
        """
        return FilePath(os.path.expandvars(os.path.expanduser(self)))

    def isabs(self):
        """Check if this is an absolute path.

        Returns:
            bool -- True if absolute path
        """
        return os.path.isabs(self)

    def is_ascii(self):
        try:
            self.encode('ascii')
        except (UnicodeDecodeError, UnicodeEncodeError):
            return False
        else:
            return True
