# Copyright (C) 2001,2002 Python Software Foundation
# Author: che@debian.org (Ben Gertzfield)

try:
    unicode
except NameError:
    def _is_unicode(x):
        return 1==0
else:
    def _is_unicode(x):
        return isinstance(x, unicode)
    
from email.Encoders import encode_7or8bit
import email.base64MIME
import email.quopriMIME



# Flags for types of header encodings
QP     = 1  # Quoted-Printable
BASE64 = 2  # Base64

# In "=?charset?q?hello_world?=", the =?, ?q?, and ?= add up to 7
MISC_LEN = 7

DEFAULT_CHARSET = 'us-ascii'



# Defaults
CHARSETS = {
    # input        header enc  body enc output conv
    'iso-8859-1':  (QP,        QP,      None),
    'iso-8859-2':  (QP,        QP,      None),
    'us-ascii':    (None,      None,    None),
    'big5':        (BASE64,    BASE64,  None),
    'gb2312':      (BASE64,    BASE64,  None),
    'euc-jp':      (BASE64,    None,    'iso-2022-jp'),
    'shift_jis':   (BASE64,    None,    'iso-2022-jp'),
    'iso-2022-jp': (BASE64,    None,    None),
    'koi8-r':      (BASE64,    BASE64,  None),
    'utf-8':       (BASE64,    BASE64,  'utf-8'),
    }

# Aliases for other commonly-used names for character sets.  Map
# them to the real ones used in email.
ALIASES = {
    'latin_1': 'iso-8859-1',
    'latin-1': 'iso-8859-1',
    'ascii':   'us-ascii',
    }

# Map charsets to their Unicode codec strings.  Note that the Japanese
# examples included below do not (yet) come with Python!  They are available
# from http://pseudo.grad.sccs.chukyo-u.ac.jp/~kajiyama/python/

# The Chinese and Korean codecs are available from SourceForge:
#
#     http://sourceforge.net/projects/python-codecs/
#
# although you'll need to check them out of cvs since they haven't been file
# released yet.  You might also try to use
#
#     http://www.freshports.org/port-description.php3?port=6702
#
# if you can get logged in.  AFAICT, both the Chinese and Korean codecs are
# fairly experimental at this point.
CODEC_MAP = {
    'euc-jp':      'japanese.euc-jp',
    'iso-2022-jp': 'japanese.iso-2022-jp',
    'shift_jis':   'japanese.shift_jis',
    'gb2132':      'eucgb2312_cn',
    'big5':        'big5_tw',
    'utf-8':       'utf-8',
    # Hack: We don't want *any* conversion for stuff marked us-ascii, as all
    # sorts of garbage might be sent to us in the guise of 7-bit us-ascii.
    # Let that stuff pass through without conversion to/from Unicode.
    'us-ascii':    None,
    }



# Convenience functions for extending the above mappings
def add_charset(charset, header_enc=None, body_enc=None, output_charset=None):
    """Add charset properties to the global map.

    charset is the input character set, and must be the canonical name of a
    character set.

    Optional header_enc and body_enc is either Charset.QP for
    quoted-printable, Charset.BASE64 for base64 encoding, or None for no
    encoding.  It describes how message headers and message bodies in the
    input charset are to be encoded.  Default is no encoding.

    Optional output_charset is the character set that the output should be
    in.  Conversions will proceed from input charset, to Unicode, to the
    output charset when the method Charset.convert() is called.  The default
    is to output in the same character set as the input.

    Both input_charset and output_charset must have Unicode codec entries in
    the module's charset-to-codec mapping; use add_codec(charset, codecname)
    to add codecs the module does not know about.  See the codec module's
    documentation for more information.
    """
    CHARSETS[charset] = (header_enc, body_enc, output_charset)


def add_alias(alias, canonical):
    """Add a character set alias.

    alias is the alias name, e.g. latin-1
    canonical is the character set's canonical name, e.g. iso-8859-1
    """
    ALIASES[alias] = canonical


def add_codec(charset, codecname):
    """Add a codec that map characters in the given charset to/from Unicode.

    charset is the canonical name of a character set.  codecname is the name
    of a Python codec, as appropriate for the second argument to the unicode()
    built-in, or to the .encode() method of a Unicode string.
    """
    CODEC_MAP[charset] = codecname



class Charset:
    """Map character sets to their email properties.

    This class provides information about the requirements imposed on email
    for a specific character set.  It also provides convenience routines for
    converting between character sets, given the availability of the
    applicable codecs.  Given an character set, it will do its best to provide
    information on how to use that character set in an email.

    Certain character sets must be encoded with quoted-printable or base64
    when used in email headers or bodies.  Certain character sets must be
    converted outright, and are not allowed in email.  Instances of this
    module expose the following information about a character set:

    input_charset: The initial character set specified.  Common aliases
                   are converted to their `official' email names (e.g. latin_1
                   is converted to iso-8859-1).  Defaults to 7-bit us-ascii.

    header_encoding: If the character set must be encoded before it can be
                     used in an email header, this attribute will be set to
                     Charset.QP (for quoted-printable) or Charset.BASE64 (for
                     base64 encoding).  Otherwise, it will be None.

    body_encoding: Same as header_encoding, but describes the encoding for the
                   mail message's body, which indeed may be different than the
                   header encoding.

    output_charset: Some character sets must be converted before the can be
                    used in email headers or bodies.  If the input_charset is
                    one of them, this attribute will contain the name of the
                    charset output will be converted to.  Otherwise, it will
                    be None.

    input_codec: The name of the Python codec used to convert the
                 input_charset to Unicode.  If no conversion codec is
                 necessary, this attribute will be None.

    output_codec: The name of the Python codec used to convert Unicode
                  to the output_charset.  If no conversion codec is necessary,
                  this attribute will have the same value as the input_codec.
    """
    def __init__(self, input_charset=DEFAULT_CHARSET):
        # Set the input charset after filtering through the aliases
        self.input_charset = ALIASES.get(input_charset, input_charset)
        # We can try to guess which encoding and conversion to use by the
        # charset_map dictionary.  Try that first, but let the user override
        # it.
        henc, benc, conv = CHARSETS.get(self.input_charset,
                                        (BASE64, BASE64, None))
        # Set the attributes, allowing the arguments to override the default.
        self.header_encoding = henc
        self.body_encoding = benc
        self.output_charset = ALIASES.get(conv, conv)
        # Now set the codecs.  If one isn't defined for input_charset,
        # guess and try a Unicode codec with the same name as input_codec.
        self.input_codec = CODEC_MAP.get(self.input_charset,
                                         self.input_charset)
        self.output_codec = CODEC_MAP.get(self.output_charset,
                                            self.input_codec)

    def __str__(self):
        return self.input_charset.lower()

    def __eq__(self, other):
        return str(self) == str(other).lower()

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_body_encoding(self):
        """Return the content-transfer-encoding used for body encoding.

        This is either the string `quoted-printable' or `base64' depending on
        the encoding used, or it is a function in which case you should call
        the function with a single argument, the Message object being
        encoded.  The function should then set the Content-Transfer-Encoding:
        header itself to whatever is appropriate.

        Returns "quoted-printable" if self.body_encoding is QP.
        Returns "base64" if self.body_encoding is BASE64.
        Returns "7bit" otherwise.
        """
        if self.body_encoding == QP:
            return 'quoted-printable'
        elif self.body_encoding == BASE64:
            return 'base64'
        else:
            return encode_7or8bit

    def convert(self, s):
        """Convert a string from the input_codec to the output_codec."""
        if self.input_codec <> self.output_codec:
            return unicode(s, self.input_codec).encode(self.output_codec)
        else:
            return s

    def to_splittable(self, s):
        """Convert a possibly multibyte string to a safely splittable format.

        Uses the input_codec to try and convert the string to Unicode, so it
        can be safely split on character boundaries (even for double-byte
        characters).

        Returns the string untouched if we don't know how to convert it to
        Unicode with the input_charset.

        Characters that could not be converted to Unicode will be replaced
        with the Unicode replacement character U+FFFD.
        """
        if _is_unicode(s) or self.input_codec is None:
            return s
        try:
            return unicode(s, self.input_codec, 'replace')
        except LookupError:
            # Input codec not installed on system, so return the original
            # string unchanged.
            return s

    def from_splittable(self, ustr, to_output=1):
        """Convert a splittable string back into an encoded string.

        Uses the proper codec to try and convert the string from
        Unicode back into an encoded format.  Return the string as-is
        if it is not Unicode, or if it could not be encoded from
        Unicode.

        Characters that could not be converted from Unicode will be replaced
        with an appropriate character (usually '?').

        If to_output is true, uses output_codec to convert to an encoded
        format.  If to_output is false, uses input_codec.  to_output defaults
        to 1.
        """
        if to_output:
            codec = self.output_codec
        else:
            codec = self.input_codec
        if not _is_unicode(ustr) or codec is None:
            return ustr
        try:
            return ustr.encode(codec, 'replace')
        except LookupError:
            # Output codec not installed
            return ustr

    def get_output_charset(self):
        """Return the output character set.

        This is self.output_charset if that is set, otherwise it is
        self.input_charset.
        """
        return self.output_charset or self.input_charset

    def encoded_header_len(self, s):
        """Return the length of the encoded header string."""
        cset = self.get_output_charset()
        # The len(s) of a 7bit encoding is len(s)
        if self.header_encoding is BASE64:
            return email.base64MIME.base64_len(s) + len(cset) + MISC_LEN
        elif self.header_encoding is QP:
            return email.quopriMIME.header_quopri_len(s) + len(cset) + MISC_LEN
        else:
            return len(s)

    def header_encode(self, s, convert=0):
        """Header-encode a string, optionally converting it to output_charset.

        If convert is true, the string will be converted from the input
        charset to the output charset automatically.  This is not useful for
        multibyte character sets, which have line length issues (multibyte
        characters must be split on a character, not a byte boundary); use the
        high-level Header class to deal with these issues.  convert defaults
        to 0.

        The type of encoding (base64 or quoted-printable) will be based on
        self.header_encoding.
        """
        cset = self.get_output_charset()
        if convert:
            s = self.convert(s)
        # 7bit/8bit encodings return the string unchanged (modulo conversions)
        if self.header_encoding is BASE64:
            return email.base64MIME.header_encode(s, cset)
        elif self.header_encoding is QP:
            return email.quopriMIME.header_encode(s, cset)
        else:
            return s

    def body_encode(self, s, convert=1):
        """Body-encode a string and convert it to output_charset.

        If convert is true (the default), the string will be converted from
        the input charset to output charset automatically.  Unlike
        header_encode(), there are no issues with byte boundaries and
        multibyte charsets in email bodies, so this is usually pretty safe.

        The type of encoding (base64 or quoted-printable) will be based on
        self.body_encoding.
        """
        if convert:
            s = self.convert(s)
        # 7bit/8bit encodings return the string unchanged (module conversions)
        if self.body_encoding is BASE64:
            return email.base64MIME.body_encode(s)
        elif self.header_encoding is QP:
            return email.quopriMIME.body_encode(s)
        else:
            return s
