'''
monkeypatch for qrcode library glog(0) bug

The qrcode library's Polynomial.__mod__ crashes with ValueError("glog(0)")
when data has long runs of zero bytes, because glog(0) is undefined in GF(256).
This patch skips leading zero coefficients before computing the ratio.

>>> qr_image = qrcode.make(bytes(260))
>>> qr_image is not None
True
'''
import qrcode  # pylint: disable=unused-import
from qrcode.base import Polynomial, glog, gexp


def _safe_mod(self, other):
    '''
    GF(256) polynomial modulus that handles leading zero coefficients

    >>> p1 = Polynomial([0, 1, 2], 0)
    >>> p2 = Polynomial([1, 1], 0)
    >>> result = p1 % p2
    >>> isinstance(result, Polynomial)
    True
    '''
    difference = len(self) - len(other)
    if difference < 0:
        return self
    if self[0] == 0:
        return Polynomial(list(self)[1:] + [0], 0) % other
    ratio = glog(self[0]) - glog(other[0])
    num = [
        item ^ gexp(glog(other_item) + ratio)
        for item, other_item in zip(self, other)
    ]
    if difference:
        num.extend(self[-difference:])
    return Polynomial(num, 0) % other


Polynomial.__mod__ = _safe_mod
