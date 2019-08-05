#!python
#cython: language_level=3, boundscheck=False, wraparound=False, nonecheck=False, initializedcheck=False

cimport cython
import numpy as numpy
cimport numpy as numpy
DTYPE = numpy.uint8
ctypedef numpy.uint8_t DTYPE_t
#!python
@cython.wraparound (False) # turn off negative indexing
@cython.boundscheck(False) # turn off bounds-checking
@cython.nonecheck(False)
def encode8bImage2RLE(numpy.ndarray[DTYPE_t,ndim=1] imgArray):
    """ Converts numpy 1D/uint8 array (1 byte per color) to RLE encoded byte string.
        This pyx code is about 30x faster than numpy code in py file

        Encoding scheme:
            Highest bit of each byte is color (black or white)
            Lowest 7 bits of each byte is repetition of that color, with max of 125 / 0x7D
        Credits for speed to:
            https://kogs-www.informatik.uni-hamburg.de/~seppke/content/teaching/wise1314/20131128_letsch-gries-boomgarten-cython.pdf
            https://stackoverflow.com/questions/53135050/why-is-cython-only-20-faster-on-runlengthencode-b-w-image
    """
    # Make room for rleData (size equal to nr of pixels to encode should suffice)
    cdef numpy.ndarray [DTYPE_t,ndim=1] rleData = numpy.zeros((3686400),dtype=DTYPE)

    # Some constants for nr of pixels and last pixelnr
    cdef unsigned int nrPixels = 3686400 #(width, height) = (1440, 2560)
    cdef unsigned int lastPixel = nrPixels - 1

    # Count number of pixels with same color up until 0x7D/125 repetitions
    cdef unsigned char color = 0
    cdef unsigned char prevColor = 0
    cdef unsigned char r
    cdef unsigned char nrOfColor = 0
    cdef unsigned char encValue = 0
    cdef unsigned int pixelNr
    cdef unsigned int nrBytes=0
    prevColor = imgArray[0] >> 7 #prevColor = nocolor
    for pixelNr in range(nrPixels):
        r = imgArray[pixelNr]
        color = r >> 7 #if (r<128) color = 1 else: color = 0
        if color == prevColor and nrOfColor < 0x7D:# and not isLastPixel:
            nrOfColor = nrOfColor + 1
        else:
            encValue = (prevColor << 7) | nrOfColor  # push color (B/W) to highest bit and repetitions to lowest 7 bits.
            rleData[nrBytes]=encValue
            nrBytes = nrBytes+1
            prevColor = color
            nrOfColor = 1
    # Handle lastpixel, we did nrOfColor++ once too many
    nrOfColor=nrOfColor-1
    encValue = (prevColor << 7) | nrOfColor  # push color (B/W) to highest bit and repetitions to lowest 7 bits.
    rleData[nrBytes] = encValue
    nrBytes = nrBytes + 1

    # Remove excess bytes and return rleData
    rleData=rleData[:nrBytes]
    return bytes(rleData)

def decodeRLE28bImage(bytes rleData):
    """ Decodes a RLE byte array from PhotonFile layer image to a numpy array
        Based on: https://gist.github.com/itdaniher/3f57be9f95fce8daaa5a56e44dd13de5
        Encoding scheme:
            Highest bit of each byte is color (black or white)
            Lowest 7 bits of each byte is repetition of that color, with max of 125 / 0x7D
    """

    cdef unsigned int nrPixels = 3686400 #(width, height) = (1440, 2560)
    cdef numpy.ndarray [DTYPE_t,ndim=1] imgArray = numpy.zeros((nrPixels),dtype=DTYPE)
    cdef unsigned char b 
    cdef unsigned char nr
    cdef unsigned char val
    cdef unsigned int idx 
    cdef unsigned char i
    
    # Decode bytes to colors and draw lines of that color on the pygame surface
    idx = 0
    for b in rleData:
        # From each byte retrieve color (highest bit) and number of pixels of that color (lowest 7 bits)
        nr = b & ~(1 << 7)  # turn highest bit of
        val = b >> 7  # only read 1st bit
                
        # The surface to draw on is smaller (scale) than the file (1440x2560 pixels)
        if val!=0:
            for i in range(nr):
              imgArray[idx+i]=255
        idx=idx+nr
    return imgArray
    
def RLEPixels(bytes rleData):
    """ Calculates nr of pixels in RLE byte array from PhotonFile layer image
        Based on: https://gist.github.com/itdaniher/3f57be9f95fce8daaa5a56e44dd13de5
        Encoding scheme:
            Highest bit of each byte is color (black or white)
            Lowest 7 bits of each byte is repetition of that color, with max of 125 / 0x7D
    """

    cdef unsigned char b 
    cdef unsigned char nr
    cdef unsigned char val
    cdef unsigned int nrPixels
    
    nrPixels=0
    # Decode bytes to colors and draw lines of that color on the pygame surface
    for b in rleData:
        # From each byte retrieve color (highest bit) and number of pixels of that color (lowest 7 bits)
        nr = b & ~(1 << 7)  # turn highest bit of
        val = b >> 7  # only read 1st bit
        if val!=0: nrPixels=nrPixels+nr
    return nrPixels    
