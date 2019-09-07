"""
Loads/Save .photon files (from the Anycubic Photon Slicer) in memory and allows editing of settings and bitmaps.

Version: 25 jun 2019
Author:  Nard Janssens

Todo:
edit getBitmap2
fix layerheight on layers.delete and insert
flip layers(tack) x-y, hor, vertical
show footprint of stack....combine layers to image using gray scale
"""

# Style Guide:
# module_name, package_name, ClassName, method_name, 
# ExceptionName, function_name, 
# GLOBAL_CONSTANT_NAME, global_var_name, instance_var_name, 
# function_parameter_name, local_var_name

__version__ = "alpha"
__author__ = "Nard Janssens, Vinicius Silva, Robert Gowans, Ivan Antalec, Leonardo Marques - See Github PhotonFileUtils"

import os
import sys
import copy
import math
import struct
from math import *
import time

import multiprocessing
import time

import RLE

try:
    import numpy
    numpyAvailable = True
    #print("Numpy library available.")
except ImportError:
    numpyAvailable = False
    raise Exception ("PhotonFile needs the numpy library!")
    #print ("Numpy library not found.")

try:
    import cv2 
    cv2Available = True
    #print("Numpy library available.")
except ImportError:
    cv2Available = False
    raise Exception ("PhotonFile needs the OpenCV2 library!")
    #print ("Numpy library not found.")

########################################################################################################################
## Define Data Types
#########################################################################################################################

# Data type constants
tpByte = 0
tpChar = 1
tpInt = 2
tpFloat = 3
tpTypeNames=("byte","char","int","float")
nrFloatDigits = 4

def convBytes(bytes:bytes, bType:int):
    """ Converts all photonfile types to bytes. """
    nr = None
    if bType == tpInt:
        nr = bytes_to_int(bytes)
    if bType == tpFloat:
        nr = round(bytes_to_float(bytes),ndigits=nrFloatDigits)
    if bType == tpByte:
        nr = bytes_to_hex(bytes)
    return nr

def convVal(val):
    """ Converts all photonfile types to bytes. """
    nr = None
    if type(val) == int:
        nr = int_to_bytes(val)
        return nr
    if type(val) == float:
        nr = float_to_bytes(val)
        return nr
    raise Exception("PhotonFile.convVal received unhandled var type",type(val),"!")
########################################################################################################################
## File structure
########################################################################################################################

# This is the data structure of photon file. For each variable we need to know
#   Title string to display user, nr bytes to read/write, type of data stored, editable
#   Each file consists of
#     - General info                                            ( pfStruct_Header,      Header)
#     - Two previews which contain meta-info an raw image data  ( pfStruct_Previews,    Previews)
#     - For each layer meta-info                                ( pfStruct_LayerDef,   LayerDefs)
#     - For each layer raw image data                           ( pfStruct_LayerData,   LayerData)

nrLayersString = "# Layers" #String is used in multiple locations and thus can be edited here

pfStruct_Header = [
    ("Header",              8, tpByte,  False, ""),
    ("Bed X (mm)",          4, tpFloat, True,  "Short side of the print bed."),
    ("Bed Y (mm)",          4, tpFloat, True,  "Long side of the print bed."),
    ("Bed Z (mm)",          4, tpFloat, True,  "Maximum height the printer can print."),
    ["padding",         3 * 4, tpByte,  False, ""], # 3 ints
    ("Layer height (mm)",   4, tpFloat, True,  "Default layer height."),
    ("Exp. time (s)",       4, tpFloat, True,  "Default exposure time."),
    ("Exp. bottom (s)",     4, tpFloat, True,  "Exposure time for bottom layers."),
    ("Off time (s)",        4, tpFloat, True,  "Time UV is turned of between layers. \n Minimum is 6.5 sec, the time to rise the \n build plate and dip back in the resin."),
    ("# Bottom Layers",     4, tpInt,   True,  "Number of bottom layers.\n (These have different exposure time.)"),
    ("Resolution X",        4, tpInt,   True,  "X-Resolution of the screen through \n which the layer image is projected."),
    ("Resolution Y",        4, tpInt,   True,  "Y-Resolution of the screen through \n which the layer image is projected." ),
    ("Preview 0 (addr)",    4, tpInt,   False, "Address where the metadata \n of the High Res preview image can be found."),  # start of preview 0
    ("Layer Defs (addr)",   4, tpInt,   False, "Address where the metadata \n for the layer images can be found."),  # start of layerDefs
    (nrLayersString,        4, tpInt,   False, "Number of layers this file has."),
    ("Preview 1 (addr)",    4, tpInt,   False, "Address where the metadata of the \n Low Res preview image can be found."),  # start of preview 1
    ("unknown6",            4, tpInt,   False, ""),
    ("Proj.type-Cast/Mirror", 4, tpInt, False, "LightCuring/Projection type:\n 1=LCD_X_MIRROR \n 0=CAST"),   #LightCuring/Projection type // (1=LCD_X_MIRROR, 0=CAST)
    ["padding tail",         6 * 4, tpByte,  False, ""]  # 6 ints 
]

pfStruct_Previews = [
    ("Resolution X",        4, tpInt,   False, "X-Resolution of preview pictures."),
    ("Resolution Y",        4, tpInt,   False, "Y-Resolution of preview pictures."),
    ("Image Address",       4, tpInt,   False, "Address where the raw \n image can be found."),  # start of rawData0
    ("Data Length",         4, tpInt,   False, "Size [in bytes) of the \n raw image."),  # size of rawData0
    ["padding",         4 * 4, tpByte,  False, ""],  # 4 ints
    ("Image Data",         -1, tpByte,  False, "The raw image."),
    ["padding tail",        0, tpByte,  False, ""]
]

pfStruct_Previews_Padding = ["padding",            0, tpByte,  False, ""]

# The exposure time and off times are ignored by Photon printer, layerheight not and is cumulative
pfStruct_LayerDef = [
    ("Layer height (mm)",   4, tpFloat, True,  "Height at which this layer \n should be printed."),
    ("Exp. time (s)",       4, tpFloat, False, "Exposure time for this layer.\n [Based on General Info.)"),
    ("Off time (s)",        4, tpFloat, False, "Off time for this layer.\n (Based on General Info.)"),
    ("Image Address",       4, tpInt,   False, "Address where the raw image \n can be found."),#dataStartPos -> Image Address
    ("Data Length",         4, tpInt,   False, "Size (in bytes) of the raw image."),  #size of rawData+lastByte(1)
    ["padding tail",         4 * 4, tpByte,  False, ""] # 4 ints
]

pfStruct_LayerDefs_Padding = ["padding",            0, tpByte,  False, ""]

pfStruct_LayerData = [
    ("Raw",              -1, tpByte, True, "rle encoded bytes"),
    ["padding tail",          0, tpByte, False, ""]
]

pfStruct_LayerDatas_Padding = ["padding",            0, tpByte,  False, ""] # after all Datas until end of file


KNOWN_SIGNATURES={
    "H-12-24 / P0-16-0 / Pt-0 / L0-16 / Lt-0 / D0-0 / Dt-0":"ACPhotonSlicer",
    "H-12-28 / P0-16-0 / Pt-60 / L0-16 / Lt-0 / D0-0 / Dt-0":"ChituBox 1.4.0"
}

layerForecolor=(167,34,252)

def get_pfStructProp(pfStruct,name:str):
    for prop in pfStruct:
        (bTitle, bNr, bType, bEditable,bHint) = prop
        if bTitle==name: return prop
    return None        

def set_pfStruct(signatureName:str):
    PROP_LENGTH=1
    for sign_id,sign_name in KNOWN_SIGNATURES.items():
        if signatureName==sign_name:  
            vals = sign_id.split("/")
            get_pfStructProp(pfStruct_Header,"padding")[PROP_LENGTH]=int(vals[0].split('-')[1])
            get_pfStructProp(pfStruct_Header,"padding tail")[PROP_LENGTH]=int(vals[0].split('-')[2])
            get_pfStructProp(pfStruct_Previews,"padding")[PROP_LENGTH]=int(vals[1].split('-')[1])
            get_pfStructProp(pfStruct_Previews,"padding tail")[PROP_LENGTH]=int(vals[1].split('-')[2])
            pfStruct_Previews_Padding [PROP_LENGTH] = int(vals[2].split('-')[1])
            get_pfStructProp(pfStruct_LayerDef,"padding tail")[PROP_LENGTH]=int(vals[3].split('-')[1])
            pfStruct_LayerDefs_Padding [PROP_LENGTH] = int(vals[4].split('-')[1])
            get_pfStructProp(pfStruct_LayerData,"padding tail")[PROP_LENGTH] = int(vals[5].split('-')[1])
            pfStruct_LayerDatas_Padding [PROP_LENGTH] = int(vals[6].split('-')[1])

########################################################################################################################
## Convert byte string to hex string
########################################################################################################################
def retrieve_name(var):
    import inspect
    callers_local_vars = inspect.currentframe().f_back.f_locals.items()
    return [var_name for var_name, var_val in callers_local_vars if var_val is var]
def debugp(var):
    print (retrieve_name(var),":",var)

########################################################################################################################
## Convert byte string to hex string
########################################################################################################################

def hexStr(bytes:bytes):
    if isinstance(bytes, bytearray):
        return ' '.join(format(h, '02X') for h in bytes)
    if isinstance(bytes, int):
        return format(bytes, '02X')
    return ("No Byte (string)")

########################################################################################################################
## Methods to convert bytes (strings) to python variables and back again
########################################################################################################################

def bytes_to_int(bytes:bytes):
    """ Converts list or array of bytes to an int. """
    result = 0
    for b in reversed(bytes):
        result = result * 256 + int(b)
    return result

def bytes_to_float(inbytes:bytes):
    """ Converts list or array of bytes to an float. """
    bits = bytes_to_int(inbytes)
    mantissa = ((bits & 8388607) / 8388608.0)
    exponent = (bits >> 23) & 255
    sign = 1.0 if bits >> 31 == 0 else -1.0
    if exponent != 0:
        mantissa += 1.0
    elif mantissa == 0.0:
        return sign * 0.0
    return sign * pow(2.0, exponent - 127) * mantissa

def bytes_to_hex(bytes:bytes):
    """ Converts list or array of bytes to an hex. """
    return ' '.join(format(h, '02X') for h in bytes)

def hex_to_bytes(hexStr:str):
    """ Converts hex to array of bytes. """
    return bytearray.fromhex(hexStr)

def int_to_bytes(intVal:int):
    """ Converts POSITIVE int to bytes. """
    return intVal.to_bytes(4, byteorder='little')

def float_to_bytes(floatVal:float):
    """ Converts POSITIVE floats to bytes.
        Based heavily upon http: //www.simplymodbus.ca/ieeefloats.xls
    """
    # Error when floatVal=0.5
    return struct.pack('f',floatVal)

    if floatVal == 0: return (0).to_bytes(4, byteorder='big')

    sign = -1 if floatVal < 0 else 1
    firstBit = 0 if sign == 1 else 1
    exponent = -127 if abs(floatVal) < 1.1754943E-38 else floor(log(abs(floatVal), 10) / log(2, 10))
    exponent127 = exponent + 127
    mantissa = floatVal / pow(2, exponent) / sign
    substract = mantissa - 1
    multiply = round(substract * 8388608)
    div256_1 = multiply / 256
    divint_1 = int(div256_1)
    rem_1 = int((div256_1 - divint_1) * 256)
    div256_2 = divint_1 / 256
    divint_2 = int(div256_2)
    rem_2 = int((div256_2 - divint_2) * 256)

    bin1 = (exponent127 & 0b11111110) >> 1 | firstBit << 7
    bin2 = (exponent127 & 0b00000001) << 7 | divint_2
    bin3 = rem_2
    bin4 = rem_1
    # print ("ALT: ",bin(bin1_new), bin(bin2_new),bin(bin3_new),bin(bin4_new))
    bin1234 = bin1 | bin2 << 8 | bin3 << 16 | bin4 << 24
    return bin1234.to_bytes(4, byteorder='big')


########################################################################################################################
## Class PreviewOps
########################################################################################################################

class PreviewOps:
    '''
    This is an internal class to provide nicely structures PhotonFile class
    All methods are provided to user via PhotonFile.previews interface
    - PhotonFile.previews.get (previewNr,retType)-> PIL.Image, byte array,numpy,Pygame.Surface
    - PhotonFile.previews.save (previewNr,file)
    - PhotonFile.previews.replace (previewNr,file/image/numpy/surface/bytearray)
    - PhotonFile.previews.__decodeRLE224bImage(rleData:bytes,w:int,h:int)

    - PhotonFile.layers.__previewPropType(propID:str)->int:
    - PhotonFile.layers.setProperty(previewNr,idString,value)
    - PhotonFile.layers.getProperty(previewNr,idString)
    '''
 
    import PhotonFile

    photonfile:PhotonFile=None
    Previews:[{},{}]=None
 
    def __init__(self, photonfile:PhotonFile,Previews:[{},{}]):
        """ Just stores photon filename. """
        self.photonfile = photonfile
        self.Previews=Previews
        assert (self.Previews != [{},{}])

    def __encode24bImage2RLE(self,filename:str) -> bytes:
        """ Converts image data from file on disk to RLE encoded byte string.
            Processes pixels one at a time (pygame.get_at) - Slow
            Encoding scheme:
                The color (R,G,B) of a pixel spans 2 bytes (little endian) and each color component is 5 bits: RRRRR GGG GG X BBBBB
                If the X bit is set, then the next 2 bytes (little endian) masked with 0xFFF represents how many more times to repeat that pixel.
        """

        image = cv2.imread(filename)
        # bitDepth = imgsurf.get_bitsize()
        # bytePerPixel = imgsurf.get_bytesize()
        width=image.shape[1]
        height=image.shape[0]
        print (image.shape,width,height)
        #print ("Size:", width, height)

        #Preview images tend to have different sizes. Check on size is thus not possible.
        #if checkSizeForNr==0 and not (width, height) == (360,186):
        #    raise Exception("Your image dimensions are off and should be 360x186 for the 1st preview.")
        #if checkSizeForNr==1 and not (width, height) == (198,101):
        #    raise Exception("Your image dimensions are off and should be 198x101 for the 1st preview.")

        # Count number of pixels with same color up until 0x7D/125 repetitions
        rleData = bytearray()
        color = 0
        black = 0
        white = 1
        nrOfColor = 0
        prevColor = None
        for y in range(height):
            for x in range(width):
                #print (x,y)
                # print (imgsurf.get_at((x, y)))
                color = image[y, x] # (r, g, b, a)
                if prevColor is None: prevColor = color
                isLastPixel = (x == (width - 1) and y == (height - 1))
                #print ("prevColor",type(prevColor),prevColor)
                #print ("color",type(color),color)
                if (color == prevColor).all() and nrOfColor < 0x0FFF and not isLastPixel:
                    nrOfColor = nrOfColor + 1
                else:
                    # print (color,nrOfColor,nrOfColor<<1)
                    R=prevColor[0]
                    G=prevColor[1]
                    B=prevColor[2]
                    if nrOfColor>1:
                        X=1
                    else:
                        X=0
                    # build 2 or 4 bytes (depending on X
                    # The color (R,G,B) of a pixel spans 2 bytes (little endian) and
                    # each color component is 5 bits: RRRRR GGG GG X BBBBB
                    R = int(round(R / 255 * 31))
                    G = int(round(G / 255 * 31))
                    B = int(round(B / 255 * 31))
                    #print ("X,r,g,b",X,R,G,B)
                    encValue0=R<<3 | G>>2
                    encValue1=(((G & 0b00000011)<<6) | X<<5 | B)
                    if X==1:
                        nrOfColor=nrOfColor-1 # write one less than nr of pixels
                        encValue2=nrOfColor>>8
                        encValue3=nrOfColor & 0b000000011111111
                        #seems like nr bytes pixels have 0011 as start
                        encValue2=encValue2 | 0b00110000

                    # save bytes
                    rleData.append(encValue1)
                    rleData.append(encValue0)
                    if X==1:
                        rleData.append(encValue3)
                        rleData.append(encValue2)

                    # search next color
                    prevColor = color
                    nrOfColor = 1
        #print ("len",len(rleData))
        return (width,height,bytes(rleData))
    
    def __decodeRLE2Image24b(self,rleData,w:int,h:int) -> numpy.ndarray: 
        # Make room for new image
        imgArray=numpy.zeros((w,h,3),dtype=numpy.uint8)       

        # Decode bytes to colors and draw lines of that color on the pygame surface
        idx = 0
        pixelIdx = 0
        while idx < len(rleData):
            # Combine 2 bytes Little Endian so we get RRRRR GGG GG X BBBBB (and advance read byte counter)
            b12 = rleData[idx + 1] << 8 | rleData[idx + 0]
            idx += 2
            # Retrieve colr components and make pygame color tuple
            #red = round(((b12 >> 11) & 0x1F) / 31 * 255)
            red = round(((b12 >> 11) & 0x1F) << 3 )
            #green = round(((b12 >> 6) & 0x1F) / 31 * 255)
            green = round(((b12 >> 6) & 0x1F) << 3 )
            #blue = round(((b12 >> 0) & 0x1F) / 31 * 255)
            blue = round((b12 & 0x1F) << 3 )
            col = (red, green, blue)

            # If the X bit is set, then the next 2 bytes (little endian) masked with 0xFFF represents how many more times to repeat that pixel.
            nr = 1
            if b12 & 0x20:
                nr12 = rleData[idx + 1] << 8 | rleData[idx + 0]
                idx += 2
                nr += nr12 & 0x0FFF

            # Draw (nr) many pixels of the color
            for i in range(0, nr, 1):
                x = int((pixelIdx % w))
                y = int((pixelIdx / w))
                imgArray[x,y,0]=red
                imgArray[x,y,1]=green
                imgArray[x,y,2]=blue
                pixelIdx += 1

        return imgArray
                
    def get(self, prevNr:int, retType:str='i')->(bytes,numpy.ndarray):
        """ Decodes a RLE byte array from PhotonFile object to a pygame surface.
            Based on https://github.com/Reonarudo/pcb2photon/issues/2
            Encoding scheme:
                The color (R,G,B) of a pixel spans 2 bytes (little endian) and each color component is 5 bits: RRRRR GGG GG X BBBBB
                If the X bit is set, then the next 2 bytes (little endian) masked with 0xFFF represents how many more times to repeat that pixel.
        """

        # Tell PhotonFile we are drawing so GUI can prevent too many calls on getBitmap
        self.photonfile.isDrawing = True

        # Retrieve resolution of preview image and set pygame surface to that size.
        w = bytes_to_int(self.photonfile.Previews[prevNr]["Resolution X"])
        h = bytes_to_int(self.photonfile.Previews[prevNr]["Resolution Y"])
        s = bytes_to_int(self.photonfile.Previews[prevNr]["Data Length"])
            
        # Retrieve raw image data and add last byte to complete the byte array
        rleData = self.photonfile.Previews[prevNr]["Image Data"]

        numpyArray2Duint8RGB=self.__decodeRLE2Image24b(rleData,w,h) 

        if retType[0]=='r': #byte array        
            return rleData 
        if retType[0]=='b': #byte array        
            return numpyArray2Duint8RGB.tobytes() 
        if retType[0]=='n': #numpy
            return numpyArray2Duint8RGB
        if retType[0]=='i': #cv2.Image
            return numpyArray2Duint8RGB

        # Done drawing so next caller knows that next call can be made.
        self.isDrawing = False
        raise Exception("Preview.get needs you to specify a return type (rle,bytes, numpy, Image, Surface).")


    def save(self, filepath:str, previewNr:int) -> None:
        """ Saves specified preview image in PhotonFile object as (decoded) png files in specified directory and with file precursor"""

        #  Get the preview images
        image = self.get(previewNr,retType='image')  # 0 is don't scale
        #  Save preview image to disk
        cv2.imwrite(filepath,image)
        return
 
    def replace(self, previewNr:int,filepath:str) -> None:
        """ Replace image data in PhotonFile object with new (encoded data of) image on disk."""

        # Get/encode raw data
        (width,height,rawData) = self.__encode24bImage2RLE(filepath)
        if len(rawData)==0:
            raise Exception ("Preview.replace got not import  image.")

        # Get change in image rawData size so we can correct starting addresses of higher layer images
        oldLength=bytes_to_int(self.photonfile.Previews[previewNr]["Data Length"]) #"Data Length" = len(rawData)+len(EndOfLayer)
        newLength=len(rawData)
        deltaLength=newLength-oldLength
        #print ("old, new, delta:",oldLength,newLength,deltaLength)

        # Update image settings and raw data of layer to be replaced
        self.photonfile.Previews[previewNr]["Resolution X"]= int_to_bytes(width)
        self.photonfile.Previews[previewNr]["Resolution Y"]= int_to_bytes(height)

        self.photonfile.Previews[previewNr]["Data Length"] = int_to_bytes(len(rawData))
        self.photonfile.Previews[previewNr]["Image Data"] = rawData

        # Update Header info about "Preview 1 (addr)"
        if previewNr==0: # then the "Preview 1 (addr)" shifts
            curAddr=bytes_to_int(self.photonfile.Header["Preview 1 (addr)"])
            newAddr = curAddr + deltaLength
            self.photonfile.Header["Preview 1 (addr)"]=int_to_bytes(newAddr)
        # Update Preview[1] info about "Preview 1 (addr)"
            curAddr=bytes_to_int(self.photonfile.Previews[1]["Image Address"])
            newAddr = curAddr + deltaLength
            self.photonfile.Previews[1]["Image Address"]=int_to_bytes(newAddr)

        #Always Header info about layerdefs shifts
        curAddr = bytes_to_int(self.photonfile.Header["Layer Defs (addr)"])
        newAddr = curAddr + deltaLength
        self.photonfile.Header["Layer Defs (addr)"] = int_to_bytes(newAddr)

        # Update start addresses of RawData of all following images
        nLayers=self.photonfile.layers.count()
        for rLayerNr in range(0,nLayers):
            curAddr=bytes_to_int(self.photonfile.LayerDefs[rLayerNr]["Image Address"])
            newAddr=curAddr+deltaLength
            self.photonfile.LayerDefs[rLayerNr]["Image Address"]= int_to_bytes(newAddr)

    def __previewPropType(self,propID:str)->int:
        for bTitle, bNr, bType, bEditable,bHint in pfStruct_Previews:
            if bTitle==propID:
                return bType
    
    def getProperty(self,previewNr:int,propID:str)->(float,int,bytes):
        valbytes = self.photonfile.Previews[previewNr][propID] 
        valtype  = self.__previewPropType(propID)
        return convBytes(valbytes,valtype)

    def setProperty(self,previewNr:int,propID:str,value):
        valtype  = self.__previewPropType(propID)
        if (type(value) is int) and valtype==tpInt:
            self.photonfile.Previews[previewNr][propID] = int_to_bytes(value)
            return
        if (type(value) is float) and valtype==tpFloat:
            self.photonfile.Previews[previewNr][propID] = float_to_bytes(value)
            return
        raise Exception(f"Preview.setProperty go an invalid type passed. Property '{propID}' needs {self.photongfile.tpTypeNames[valtype]} got {type(value)}.")
        
########################################################################################################################
## Class LayerOps
########################################################################################################################

class LayerOps:
    import PhotonFile
    '''
    This is an internal class to provide nicely structures PhotonFile class
    All methods are provided to user via PhotonFile.layers interface
    - PhotonFile.layers.__getall (retType) -> PIL.Image,bytes,numpy,Pygame.Surface
    - PhotonFile.layers.__saveall (folder:str)
    - PhotonFile.layers.__replaceall (images:str,list(rlestack))
    - PhotonFile.layers.__headerPropType (propID:str)->int
    
    - PhotonFile.layers.save (layerNr,file)
    - PhotonFile.layers.load (dir/file, optional layernr) -> append/insert
    - PhotonFile.layers.get (layerNr,retType)-> PIL.Image, byte array,numpy,Pygame.Surface
    - PhotonFile.layers.insert (layerNr,file/image/numpy/surface/bytearray)
    - PhotonFile.layers.delete (layerNr:int)
    - PhotonFile.layers.append (file/image/numpy/surface/bytearray) (=insertBefore(nrLayers))
    - PhotonFile.layers.replace (layerNr,file/image/numpy/surface/bytearray)
    - PhotonFile.layers.copy (layerNr,layerNr)    
    - PhotonFile.layers.setProperty(layerNr,idString,value)
    - PhotonFile.layers.getProperty(layerNr,idString)
    - PhotonFile.layers.count()
    - PhotonFile.layers.height()
    - PhotonFile.layers.volume()
    
    - PhotonFile.layers.__deepcopy(dictionary)
    - PhotonFile.layers.loadFromHistory()
    - PhotonFile.layers.saveFromHistory()
    
    
    '''

    photonfile:PhotonFile=None
    LayerDefs:[]=None
    LayerData:[]=None
    __ALL_LAYERS:int=-1
    cancelReplace:bool=False
    History = []
    
    def __init__(self, photonfile:PhotonFile, LayerDefs:[],LayerData:[]):
        """ Just stores photon filename. """
        self.photonfile = photonfile
        self.LayerDefs=LayerDefs
        self.LayerData=LayerData
        self.History = []
        assert (self.LayerDefs != [])
        assert (self.LayerData != [])

    # Internals for multithreading
    def getAll(self):
        ''' Returns all images in the photonfile as list of rle bytearray
            Memory does not allow for list of cv2.images, numpy arrays
        ''' 
        all=list()
        #tstart=time.time()
        for layerNr in range(self.count()):
            rle=self.get(layerNr,retType='rle')
            all.append(rle)
        #print (f"100% - {round((time.time() - tstart),3)} sec." )                            
        return all

    def par_getBitmap(self,args):
        # Helper for procespoolexecutor in replaceBitmaps to call
        [layerNr,fullfilename]=args
        image = self.get(layerNr,'i')
        cv2.imwrite(fullfilename,image)
        return layerNr
    
    def saveAll(self,dirpath:str,filepre:str="",progressDialog=None):
        '''Save all images in PhotonFile object as (decoded) png files in specified directory and with file precursor"""
            Benchmark 1716 layers:
                No parallel code: 30.5 sec
                Multiprocessing:  14.7 sec
                ThreadPool:       18.5 sec
                ProcessPool:      Crash/Hang
        '''
        # Check if dirpath is a file 
        if (os.path.exists(dirpath)) and not (os.path.isdir(dirpath)):
            raise Exception("LayerOps.saveAll received '{dirpath}' as directory but is a file.")
 
        # Check if directory is present
        if not os.path.isdir(dirpath):
            os.makedirs(dirpath)
 
        # Recheck if directory is present (check for OS Error)
        if not os.path.isdir(dirpath):
            raise Exception(f"LayerOps.saveAll did not succeed in creating directory '{dirpath}'.")

        # Traverse all layers
        nLayers=self.count()
        files=[]
        for layerNr in range(0,nLayers):
            nrStr = "%04d" % layerNr
            filename = filepre
            if filepre!='': filename=filename+"-"
            filename = filename + nrStr + ".png"
            fullfilename = os.path.join(dirpath, filename)
            files.append([layerNr,fullfilename])

        tstart=time.time()
        cpus=multiprocessing.cpu_count()
        pool=multiprocessing.Pool(processes=cpus-1)
        r=pool.map_async(self.par_getBitmap,files)
        pool.close()
        #pool.join()
        
        number_start=r._number_left
        while True:
            perc=round(100*(number_start-r._number_left)/number_start)
            sys.stderr.write('\rExporting... ')
            sys.stderr.write(str(perc))
            sys.stderr.write('% ')
            if progressDialog: progressDialog.setProgressPerc(perc)
            time.sleep(0.5)
            if (r._number_left == 0): 
                print (f"100% - {round((time.time() - tstart),1)} sec." )
                if progressDialog: progressDialog.setProgressPerc(100)
                break    
 
        return True

    def par_encodeImageFile2Bytes(self,args):
        # Helper for procespoolexecutor in replaceBitmaps to call
        [layerNr,fullfilename]=args
        npArray=cv2.imread(fullfilename)
        if npArray.ndim==3:
            npArray=npArray[:,:,0]
        npArray_1D_uint8=npArray.flatten().astype(numpy.uint8)        
        rlebytes= RLE.encode8bImage2RLE(npArray_1D_uint8)        
        #return [layerNr,rlebytes] # results are presented to callback in order, layerNr is not needed
        return rlebytes # results are presented to callback in order, layerNr is not needed

    def replaceAll(self,images:(str,list),progressDialog=None):
        ''' Replaces all layer images with png-images available in a folder on disk.
            Images is string for folder with png or
            Images is list of rle bytearrays
        ''' 

        if type(images)==str: # directory with files
            dirPath=images
            rlestack=()
        
            # Find all png files
            direntries = os.listdir(dirPath)
            files = []
            for entry in direntries:
                fullpath = os.path.join(dirPath, entry)
                if entry.endswith("png"):
                    if not entry.startswith("_"): # on a export of images from a photon file, the preview image starts with _
                        files.append(fullpath)
            files.sort()
            # We need a list of tuples consisting of (layerNr,filename)
            files=list(enumerate(files))

            # Check if there are files available and if so check first file for correct dimensions
            if len(files) == 0: raise Exception("LayerOps.__replaceAll cannot find any files of type png!")            
        
            # Read all files in parallel and wait for result
            nLayers=len(files)
            rlestack = nLayers * [None]

            tstart=time.time()
            cpus=multiprocessing.cpu_count()
            pool=multiprocessing.Pool(processes=cpus-1)
            # results should not be reteived using callback (then we need some routine to check if all is finished)
            r=pool.map_async(self.par_encodeImageFile2Bytes,files)
            pool.close()

            number_start=r._number_left
            while True:
                perc=round(100*(number_start-r._number_left)/number_start)
                sys.stderr.write('\rImporting... ')
                sys.stderr.write(str(perc))
                sys.stderr.write('% ')
                if progressDialog: progressDialog.setProgressPerc(perc)
                time.sleep(0.5)
                if (r._number_left == 0): # updates are less than 2x per second
                    print (f"100% - {round((time.time() - tstart),1)} sec." ) 
                    if progressDialog: progressDialog.setProgressPerc(100)
                    self.replaceAll(r.get(None))      
                    break    

            return
        
        if isinstance(images,list): # list of rleByteArray

            if not isinstance(images[0],bytes):
                raise Exception("LayerOps.__replaceAll only accepts a list of RLE byte arrays due to memory constraints.")
                        
            rleStack=images

            self.clear()
            for rleData in rleStack:
                    self.append(rleData)

            # Check
            for layerNr in range(self.count()-1):
                a0=bytes_to_int(self.photonfile.LayerDefs[layerNr+0]["Image Address"])
                l=bytes_to_int(self.photonfile.LayerDefs[layerNr+0]["Data Length"])
                a1=bytes_to_int(self.photonfile.LayerDefs[layerNr+1]["Image Address"])
                d=len(self.photonfile.LayerData[layerNr]["Raw"])
                t=len(self.photonfile.LayerData[layerNr]["padding tail"])
                if d!=l:
                    assert(True==False)
                if (a1-a0)!=(d+t):
                    assert(True==False)
                if (a1-a0)!=l:
                    assert(True==False)
                
            return

        # If we reach this point, we did not get a string or a list as input
        raise Exception("LayerOps.__replaceAll will only convert files on disk or a list of rle encoded bytestrings.")            
    nr=0

    # User functions
    def __layerPropType(self,propID:str)->int:
        for bTitle, bNr, bType, bEditable,bHint in pfStruct_LayerDef:
            if bTitle==propID:
                return bType
    
    def getProperty(self,layerNr:int,propID:str):
        valbytes = self.photonfile.LayerDefs[layerNr][propID] 
        valtype  = self.__layerPropType(propID)
        return convBytes(valbytes,valtype)

    def setProperty(self,layerNr:int,propID:str,value):
        valtype  = self.__layerPropType(propID)
        if (type(value) is int) and valtype==tpInt:
            self.photonfile.LayerDefs[layerNr][propID] = int_to_bytes(value)
            return
        if (type(value) is float) and valtype==tpFloat:
            self.photonfile.LayerDefs[layerNr][propID] = float_to_bytes(value)
            return
        raise Exception(f"LayerOps.setProperty got an invalid type passed. Property '{propID}' needs {self.photonfile.tpTypeNames[valtype]} got {type(value)}.")

    def print(self,layerNr:int):
        print ("Layer Nr",layerNr)
        print ("  Layer height (mm): ",bytes_to_float(self.photonfile.LayerDefs[layerNr]["Layer height (mm)"]))
        print ("  Exp. time (s)    : ",bytes_to_float(self.photonfile.LayerDefs[layerNr]["Exp. time (s)"]))
        print ("  Off time (s)     : ",bytes_to_float(self.photonfile.LayerDefs[layerNr]["Off time (s)"]))
        print ("  Image Address    : ",bytes_to_int(self.photonfile.LayerDefs[layerNr]["Image Address"]))
        print ("  Data Length      : ",bytes_to_int(self.photonfile.LayerDefs[layerNr]["Data Length"]))
        print ("  def padding tail : ",len(self.photonfile.LayerDefs[layerNr]["padding tail"]),"'"+bytes_to_hex(self.photonfile.LayerDefs[layerNr]["padding tail"])+"'")
        print ("  Raw length)      : ",len(self.photonfile.LayerData[layerNr]["Raw"]))
        print ("  Raw padding tail : ",len(self.photonfile.LayerData[layerNr]["padding tail"]),"'"+bytes_to_hex(self.photonfile.LayerData[layerNr]["padding tail"])+"'")

    def count(self):
        """ Returns 4 bytes for number of layers as int. """
        return  bytes_to_int(self.photonfile.Header[nrLayersString])    

    def last(self):
        """ Returns 4 bytes for number of layers as int. """
        return  self.count()-1    

    def height(self,layerNr:int):
        """ Return height between two layers
        """
        # We retrieve layer height from previous layer
        if layerNr>0:
            curLayerHeight = convBytes(self.photonfile.LayerDefs[layerNr]["Layer height (mm)"],tpFloat)
            prevLayerHeight = convBytes(self.photonfile.LayerDefs[layerNr-1]["Layer height (mm)"],tpFloat)
        else:
            if self.count()>1:
                curLayerHeight = convBytes(self.photonfile.LayerDefs[layerNr+1]["Layer height (mm)"],tpFloat)
                prevLayerHeight=0
            else:
                curLayerHeight=convBytes(self.photonfile.Header["Layer height (mm)"],tpFloat)
                prevLayerHeight = 0
        return curLayerHeight-prevLayerHeight
        #print ("Delta:", deltaHeight)
    
    def load(self,path:str,layerNr:int,operation:str='append',saveToHistory=True):
        ''' operation: 'append' / 'replace'
        '''
        if operation[0]=='r': 
            self.replace(layerNr,path,saveToHistory=True)
            return
        if operation[0]=='a': 
            self.append(path,saveToHistory=True)
            return
        if layerNr==self.__ALL_LAYERS: 
            self.replaceAll(path)
            return
        raise Exception("LayerOps.load got an invalid operation. Use 'append' or 'replace'.")

    def save(self,layerNr:int, path:str):
        if layerNr==self.__ALL_LAYERS:
            self.saveAll(path)
        else:
            nrStr = "%04d" % layerNr
            if self.photonfile.filename!=None:
                filepre = os.path.join(path,os.path.basename(self.photonfile.filename))
            else:    
                filepre = os.path.join(path,"newfile")
            fullfilename = filepre + "-" + nrStr + ".png"
            print ("fullfilename",fullfilename)
            image=self.get(layerNr,retType='i')
            cv2.imwrite(fullfilename,image)
         
    def append(self,
                image:(str,numpy.ndarray,bytes),
                saveToHistory:bool=False):
        self.insert(image,self.count(),saveToHistory)

    def paste (self,layerNr:int,saveToHistory:bool=False):
        self.insert('clipboard',layerNr,saveToHistory)

    def insert( self,
                image:(str,numpy.ndarray,bytes),
                layerNr:int,
                saveToHistory:bool=False):

        deb=False

        # Check if order arguments is correct
        if type(layerNr)!=int:
            raise Exception("LayerOps.insert got wrong argument type.")

        fromClipboard:bool=False
        if type(image) is str: 
            if image == "clipboard":
                fromClipboard = True
                image=self.clipboardData["Raw"]
        
        # Check if user is in bounds
        if layerNr > self.count(): layerNr=self.count()
        if layerNr < 0: raise Exception("LayerOps.insert got negative layerNr.")
      
        # Convert image so we finally have a RLE byte array to process
        if type(image) is str: 
            im = cv2.imread(image,cv2.IMREAD_UNCHANGED)
            self.insert(im,layerNr,saveToHistory)
            return 

        if isinstance(image,numpy.ndarray): # numpy or cv2 image
            # if RGB retrieve Red channel
            if image.ndim==3:
                image=image[:,:,0]
            
            # Check if correct size
            if image.shape != (2560,1440) or image.dtype!=numpy.uint8: # Numpy Array dimensions are switched from PIL.Image dimensions
                raise Exception(f"LayerOps.insert needs an CV2 Image with dimensions of 1440x2560 and 8 bit. Got {image.shape[0]}x{image.shape[1]}x{24 if image.ndim==3 else 8} ({image.dtype})")
            
            npArray_1D_uint8=image.flatten()#.astype(numpy.uint8)        
            rleBytearray=RLE.encode8bImage2RLE(npArray_1D_uint8)
            self.insert(rleBytearray,layerNr,saveToHistory)
            return

        # Here we are inserting RLE              
        if isinstance(image,bytes): 
            if fromClipboard and self.clipboardDef==None: 
                raise Exception("LayerOps.insert got empty clipboard!")
    
            # Check if layerNr in range, could occur on undo after deleting last layer
            #   print(layerNr, "/", self. self.Layers.count())
            insertLast=False
            nLayers=len(self.photonfile.LayerDefs)
            if layerNr>nLayers: layerNr=nLayers
            if layerNr == nLayers:
                layerNr=layerNr-1 # temporary reduce layerNr
                insertLast=True
    
            if deb:
                print ("Start:")
                print ("  Insert new layer at Nr   : ",layerNr)
                print ("  Append (insertLast)      : ",insertLast)
                print ("  Layer Count              : ",self.count())
                print ("  Header: Layer Defs (addr): ",bytes_to_int(self.photonfile.Header["Layer Defs (addr)"]))
                if self.count()>0:
                    print ("  LayerDef(0): Data (addr) : ",bytes_to_int(self.photonfile.LayerDefs[0]["Image Address"]))

            # Check deltaHeight
            deltaHeight = self.photonfile.layers.height(layerNr)

            # Make duplicate of layerDef and layerData if not pasting from clipboard
            if fromClipboard == False:
                if self.count()>0:
                    self.clipboardDef=self.__realDeepCopy(self.photonfile.LayerDefs[layerNr])
                    self.clipboardDef["Data Length"]=int_to_bytes(len(image))
                    self.clipboardData=self.__realDeepCopy(self.photonfile.LayerData[layerNr])
                    self.clipboardData["Raw"]=image
                else:
                    # The exposure time and off times are ignored by Photon printer, layerheight not and is cumulative
                    self.clipboardDef={}
                    self.clipboardDef["Layer height (mm)"]= self.photonfile.Header["Layer height (mm)"]
                    self.clipboardDef["Exp. time (s)"]    = self.photonfile.Header["Exp. time (s)"]
                    self.clipboardDef["Off time (s)"]     = self.photonfile.Header["Off time (s)"]   
                    self.clipboardDef["Image Address"]    = 4 * b'\x00' 
                    self.clipboardDef["Data Length"]      = int_to_bytes(len(image))
                    self.clipboardDef["padding tail"]     = pfStruct_LayerDef [5][1]*b'\x00'
                    self.clipboardData={}
                    self.clipboardData["Raw"]             = image
                    self.clipboardData["padding tail"]    = pfStruct_LayerData [1][1]*b'\x00'
                if deb: self.printClipboard()

            # Set layerheight correctly
            if deb: print ("layerNr",layerNr)
            if layerNr==-1: # no other layer to base layer height on so we start on height = 0
                self.clipboardDef["Layer height (mm)"] = float_to_bytes(0)
            elif layerNr==0: # if first layer than the height should start at 0
                self.clipboardDef["Layer height (mm)"] = float_to_bytes(0)
            else:          # start at layer height of layer at which we insert
                curLayerHeight = bytes_to_float(self.photonfile.LayerDefs[layerNr]["Layer height (mm)"])
                self.clipboardDef["Layer height (mm)"]=float_to_bytes(curLayerHeight)
    
            # Calc length of new def
            defLength=0
            for key,val in self.clipboardDef.items():
                defLength=defLength+len(val)
            if deb:print ("defLength :",defLength)    
            if deb:print ("taillength:",len(self.photonfile.LayerDefs_padding_tail))
            
            # Set start addresses of layer in clipboard, we add 1 layer(def) so add 36 bytes
            if layerNr==-1:
                lA=(bytes_to_int(self.photonfile.Header["Layer Defs (addr)"])+
                    defLength+
                    len(self.photonfile.LayerDefs_padding_tail)
                    )
            else:
                lA=bytes_to_int(self.photonfile.LayerDefs[layerNr]["Image Address"])+defLength
                #   if lastlayer we need to add last image length
                if insertLast: lA=lA+bytes_to_int(self.LayerDefs[layerNr]["Data Length"])
            
            # Starts at 55220 with image size of 33071
            if deb:print ("New Image Address (lA):",lA)

            self.clipboardDef["Image Address"]=int_to_bytes(lA)
    
            # If we inserting last layer, we correct layerNr and layerheight
            if insertLast: 
                layerNr = layerNr + 1  # fix temporary reduced layerNr
                if layerNr>0: 
                    curHeight=bytes_to_float(self.photonfile.LayerDefs[layerNr-1]["Layer height (mm)"])
                    self.clipboardDef["Layer height (mm)"]=float_to_bytes(
                                                            curHeight+
                                                            bytes_to_float(self.photonfile.Header["Layer height (mm)"])
                                                            )
            if deb:print ("Correct layerNr because last:",layerNr)

            # Shift start addresses of RawData in all LayerDefs due to extra layerdef (36 bytes)
            if deb:print("Shift image addresses in layerdefs due to new layerdef:")
            for rLayerNr in range(0,nLayers):
                curAddr=bytes_to_int(self.LayerDefs[rLayerNr]["Image Address"])
                newAddr=curAddr+defLength # size of layerdef
                self.LayerDefs[rLayerNr]["Image Address"]= int_to_bytes(newAddr)
                if deb:print ("  layerdef",rLayerNr,"from",curAddr,"to",newAddr)
    
            # Shift start addresses of RawData in second part of LayerDefs due to extra layerdata
            if deb:print("Shift image addresses in layerdefs due to new image data:")
            deltaLayerImgAddress = bytes_to_int(self.clipboardDef["Data Length"]) #+ defLength
            for rLayerNr in range(layerNr,nLayers):
                # Adjust image address for removal of image raw data and end byte
                curAddr=bytes_to_int(self.LayerDefs[rLayerNr]["Image Address"])
                newAddr=curAddr+deltaLayerImgAddress
                self.photonfile.LayerDefs[rLayerNr]["Image Address"]= int_to_bytes(newAddr)
                # Adjust layer starting height for removal of layer
                curHeight=bytes_to_float(self.LayerDefs[rLayerNr]["Layer height (mm)"])
                newHeight=curHeight+deltaHeight
                self.photonfile.LayerDefs[rLayerNr]["Layer height (mm)"] = float_to_bytes(newHeight)
                #print ("layer, cur, new: ",rLayerNr,curAddr,newAddr, "|", curHeight,newHeight ,">",self.bytes_to_float(self.LayerDefs[rLayerNr]["Layer height (mm)"]))
                if deb:print ("  layerdef",rLayerNr,"from",curAddr,"to",newAddr)
    
            # Insert layer settings and data and reduce number of layers in header
            if layerNr<nLayers:
                self.photonfile.LayerDefs.insert(layerNr,self.clipboardDef)
                self.photonfile.LayerData.insert(layerNr,self.clipboardData)
            else:
                self.photonfile.LayerDefs.append(self.clipboardDef)
                self.photonfile.LayerData.append(self.clipboardData)
    
            self.photonfile.Header[nrLayersString]=int_to_bytes(len(self.photonfile.LayerDefs))
    
            # Make new copy so second paste will not reference this inserted objects
            self.clipboardDef = None #self.photonfile.LayerDefs[layerNr].copy()
            self.clipboardData = None #self.photonfile.LayerData[layerNr].copy()

            # Debug photonfile
            if deb:
                print ("Header: Layer Defs (addr):",bytes_to_int(self.photonfile.Header["Layer Defs (addr)"]))
                for layerNr in range(self.count()):
                    self.print(layerNr)

            # Store new data to history
            if saveToHistory: self.saveToHistory("insert",layerNr)
    
            # We finished this method and exit to prevent raise Execption
            return
 
        raise Exception(f"Layer.insert got unknown image type {type(image)}. Allowed is filename(string), 2d array (numpy.ndarray), CV2 Image, rle byte array.")

    def copy(self,layerNr:int,destination:(int,str)='clipboard',saveToHistory:bool=False):
        if destination=='clipboard': # Copy to clipboard - Make duplicate of layerDef and layerData
            self.clipboardDef=self.photonfile.LayerDefs[layerNr].copy()
            self.clipboardData=self.photonfile.LayerData[layerNr].copy()
        else:
            byteArray=self.photonfile.LayerData[layerNr]["Raw"] #self.get(layerNr=layerNr,retType='b')
            self.insert(image=byteArray,layerNr=destination)
            #SaveToHistory handled in insert
    
    def clear(self):
        self.photonfile.LayerDefs.clear()
        self.photonfile.LayerData.clear()
        self.photonfile.Header[nrLayersString]=int_to_bytes(0)

    def delete(self,layerNr:int,saveToHistory:bool=False):
        """ Deletes layer and its image data in the PhotonFile object, but store in clipboard for paste. """

        if layerNr>self.last(): layerNr=self.last()

        # Store all data to history
        if saveToHistory: self.saveToHistory("delete",layerNr)

        #deltaHeight=self.bytes_to_float(self.LayerDefs[layerNr]["Layer height (mm)"])
        deltaHeight =self.height(layerNr)
        #print ("deltaHeight:",deltaHeight)

        # Update start addresses of RawData of before deletion with size of one extra layerdef (36 bytes)
        for rLayerNr in range(0,layerNr):
            # Adjust image address for removal of image raw data and end byte
            curAddr=bytes_to_int(self.photonfile.LayerDefs[rLayerNr]["Image Address"])
            newAddr=curAddr-36 # size of layerdef
            self.photonfile.LayerDefs[rLayerNr]["Image Address"]= int_to_bytes(newAddr)

        # Update start addresses of RawData of after deletion with size of image and layerdef
        deltaLength = bytes_to_int(self.photonfile.LayerDefs[layerNr]["Data Length"]) + 36  # +1 for len(EndOfLayer)
        nLayers=self.count()
        for rLayerNr in range(layerNr+1,nLayers):
            # Adjust image address for removal of image raw data and end byte
            curAddr=bytes_to_int(self.LayerDefs[rLayerNr]["Image Address"])
            newAddr=curAddr-deltaLength
            #print ("layer, cur, new: ",rLayerNr,curAddr,newAddr)
            self.photonfile.LayerDefs[rLayerNr]["Image Address"]= int_to_bytes(newAddr)

            # Adjust layer starting height for removal of layer
            curHeight=bytes_to_float(self.photonfile.LayerDefs[rLayerNr]["Layer height (mm)"])
            newHeight=curHeight-deltaHeight
            self.photonfile.LayerDefs[rLayerNr]["Layer height (mm)"] =float_to_bytes(newHeight)

        # Store deleted layer in clipboard
        self.clipboardDef=self.photonfile.LayerDefs[layerNr].copy()
        self.clipboardData=self.photonfile.LayerData[layerNr].copy()

        # Delete layer settings and data and reduce number of layers in header
        self.photonfile.LayerDefs.remove(self.photonfile.LayerDefs[layerNr])
        self.photonfile.LayerData.remove(self.photonfile.LayerData[layerNr])
        self.photonfile.Header[nrLayersString]=int_to_bytes(self.count()-1)
        
    def replace(self,layerNr:int,image:(str,numpy.ndarray,bytes),saveToHistory:bool=False):
        # Check if order arguments is correct
        if type(layerNr)!=int:
            raise Exception("Did you switch arguments? First argument should by layerNr, second image.")

        if layerNr==self.__ALL_LAYERS: 
            self.replaceAll(image)
            return 
        
        self.insert(image,layerNr,saveToHistory)
        self.delete(layerNr+1,saveToHistory)
        
    def get(self,layerNr:int,retType:str='image'):
        if layerNr==self.__ALL_LAYERS: 
            if retType[0]=='r':
                self.getAll()                
                return
            else:
                raise Exception ("LayerOps.get only allows for 'rle' to be returned due to memory constraints.")

        rleByteArray = self.photonfile.LayerData[layerNr]["Raw"]        
        
        if retType[0]=='r': #rle array        
            return rleByteArray 

        numpyArray1Duint8 = RLE.decodeRLE28bImage(rleByteArray)

        if retType[0]=='b': #byte string (decoded)
            return numpyArray1Duint8.tobytes() 
        if retType[0]=='n': #numpy
            numpyArray2Duint8=numpyArray1Duint8.reshape(2560,1440)
            return numpyArray2Duint8
        if retType[0]=='i': #cv2.Image
            numpyArray2Duint8=numpyArray1Duint8.reshape(2560,1440,1)
            return numpyArray2Duint8

        raise Exception("LayerOps.get got an unknown return type. Use rle, bytes or image-cv2.")


    ########################################################################################################################
    ## Methods to show layer in full model
    ########################################################################################################################
    #
    # Benchmarks                                                        time (sec)
    # ScaleDown:                                                      4      2       1   
    #                                                               ----------------------
    # img=photonfile.layers.getContour(30,1,1)                              0.005   0.025  seconds
    # img=photonfile.layers.getContour(30,15,2)                             0.005   0.025  seconds
    # img=photonfile.layers.getMultiXRay(redraw=True,scaleDown=4)    1.2    2.3     6.3    seconds
    # img=photonfile.layers.getContourInShaded(30,15,scaleDown=2)    1.0    3.0     8.0    seconds
    #
    __XRAY=0
    __SHADE=1
    multilayerImageShade = None
    multilayerImageXRay = None
    multilayerImageShade_Stack=[]
    multilayerImageXRay_Stack=[]
    global layerForecolor

    def getMultiShaded(self,redraw=False,step=-1,scaleDown=2,stack=False,stacklayer=0,progressDialog=None):
        return self.__getMultiLayerImage(redraw,mode=self.__SHADE,brighten=0,step=step,scaleDown=scaleDown,stack=stack,stacklayer=stacklayer,progressDialog=progressDialog)
    def getMultiXRay(self,redraw=False,brighten=10,step=-1,scaleDown=2,stack=False,stacklayer=0,progressDialog=None):
        return self.__getMultiLayerImage(redraw,mode=self.__XRAY,brighten=brighten,step=step,scaleDown=scaleDown,stack=stack,stacklayer=stacklayer,progressDialog=progressDialog)

    def __getMultiLayerImage(self,redraw=False,
                                  mode=__XRAY,
                                  brighten=10,
                                  step=-1,
                                  scaleDown=2,
                                  stack=False,
                                  stacklayer=0,
                                  progressDialog=None):
        t=time.time()
        global multilayerImageShade_Stack,multilayerImageXray_Stack
        # Calculate how many layers we can skip for 255 grey tones
        if step==-1: step=int(self.count()/255) # usually 2550 layer per model, 0.05mm per layer, so 0.5mm per gradient
        if step < 1: step=1
        
        # Retrieve multilayerimage from memory if present
        multilayerImage=None
        if not stack:
            if mode==self.__SHADE: multilayerImage=self.multilayerImageShade
            if mode==self.__XRAY:  multilayerImage=self.multilayerImageXRay
        else:
            stacklayer=stacklayer//step
            if mode==self.__SHADE and not self.multilayerImageShade_Stack == []:
                multilayerImage=cv2.imdecode(self.multilayerImageShade_Stack[stacklayer],0)
            if mode==self.__XRAY and not self.multilayerImageXRay_Stack == []:
                multilayerImage=cv2.imdecode(self.multilayerImageXRay_Stack[stacklayer],0)

        #  Calculate if forced redraw or multi-imagelayer not in memory
        offset=self.count()*0.5 # offset color so lowest layers are not color 0,0,0        
        if multilayerImage is None or redraw==True:
            if stack: # Clear stack (probably called with redraw=True)
                if mode==self.__SHADE: multilayerImageShade_Stack=[]
                if mode==self.__XRAY:  multilayerImageXRay_Stack=[]
            multilayerImage = numpy.zeros((2560//scaleDown,1440//scaleDown),dtype=numpy.int32)
            if progressDialog!=None: progressDialog.show()
            for layerNr in range(0,self.count(),step):
                arr = self.get(layerNr,retType="numpy")
                if scaleDown!=1:arr=cv2.resize(arr,(0,0),fx=1/scaleDown,fy=1/scaleDown)
                arr = numpy.array(arr,dtype=numpy.int32)
                arr[arr==255] = offset+layerNr
                # Add new layer to multilayerImage
                if mode==self.__SHADE: numpy.maximum(arr,multilayerImage,multilayerImage)
                if mode==self.__XRAY:  multilayerImage=multilayerImage+arr
                if stack: # We need to compress each image before appending to stack to minimize mem usage
                    res=multilayerImage* (255.0/multilayerImage.max()) # recolor from 0 to 255
                    if mode==self.__XRAY: res=res*brighten             # brighten                    
                    res[res>255]=255                                   # max color
                    res=numpy.array(res,dtype=numpy.uint8)             # minimize mem usage
                    imgenc=cv2.imencode('.png', res)[1]                # compress
                    if mode==self.__SHADE:  self.multilayerImageShade_Stack.append(imgenc)
                    if mode==self.__XRAY:  self.multilayerImageXRay_Stack.append(imgenc)
                if progressDialog!=None: 
                    progressDialog.setProgressPerc(int(100*layerNr/self.count()))

            if progressDialog!=None: progressDialog.setProgressPerc(100)

            # If not stack we only rescale colors after all images are added to get maximum color resolution
            if not stack: 
                res=multilayerImage* (255.0/multilayerImage.max()) # recolor from 0 to 255
                if mode==self.__XRAY: res=res*brighten             # brighten                    
                res[res>255]=255                                   # max color
                res=numpy.array(res,dtype=numpy.uint8)             # make dtype 8 bit image and save
                multilayerImage=res
            else:
                multilayerImage=cv2.imdecode(self.multilayerImageXRay_Stack[stacklayer],0)

            # Store constructed multilayerimage in memory so on next call we can retreive this instead of reconstructing it
            if mode==self.__SHADE: self.multilayerImageShade=multilayerImage
            if mode==self.__XRAY:  self.multilayerImageXRay =multilayerImage

            if progressDialog!=None: progressDialog.hide()

        print ("elapsed",int(time.time()-t),"sec.")

        return multilayerImage
    '''
    def getContour(self,layerNr, width,scaleDown=2): 
        # This method (scaleDown=1):    0.017 sec / 2560x1440 image
        # cv2.Canny(res,64,192)         0.011 sec / 2560x1440 image
        #https://stackoverflow.com/questions/51541754/how-to-change-the-thickness-of-the-edge-contour-of-an-image
        image=self.get(layerNr,retType='numpy')
        if scaleDown!=1:image=cv2.resize(image,(0,0),fx=1/scaleDown,fy=1/scaleDown)

        bg = numpy.zeros(image.shape)
        bg=bg.astype(numpy.uint8)
        contours, _ = cv2.findContours(image.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # sort contours for area (from smallest to largest)
        contours = sorted(contours, key=cv2.contourArea)
        # We only want first x contours (otherwise too much detail which slows us down and user probably will not notice)
        contours = contours[-6:]

        # Draw contours
        for contour in contours:
            bg=cv2.drawContours(bg, [contour], 0, (255, 255, 255), width).astype(numpy.uint8)         
        return bg

    def getContourInXRay(self,layerNr=0,width=10,scaleDown=2):
        return self.__getContourInMultiLayerImage(self.__XRAY,  layerNr,width,scaleDown)
    def getContourInShaded(self,layerNr=0,width=10,scaleDown=2):
        return self.__getContourInMultiLayerImage(self.__SHADE,layerNr,width,scaleDown)
    def __getContourInMultiLayerImage(self,mode=__XRAY,layerNr=0,width=10,scaleDown=2):        
        if mode==self.__XRAY:   multilayerImage=self.getMultiXRay(scaleDown=scaleDown)
        if mode==self.__SHADE:  multilayerImage=self.getMultiShaded(scaleDown=scaleDown)
        bkg_bw  = multilayerImage                                                   # (2560 , 1440 )
        bkg_rgb = cv2.cvtColor(bkg_bw,cv2.COLOR_GRAY2RGB)                           # (2560 , 1440 , 3)
        con_bw  = self.getContour(layerNr,width,scaleDown=scaleDown)                # (2560 , 1440 )
        con_rgb = cv2.cvtColor(con_bw,cv2.COLOR_GRAY2RGB)                           # (2560 , 1440 , 3)
        con_rgb[numpy.where((con_rgb == [255,255,255]).all(axis = 2))] = layerForecolor  # (2560 , 1440 , 3)
        mask     = con_bw
        mask_inv = cv2.bitwise_not(mask)                                            # (2560 , 1440 )
        img1_bg  = cv2.bitwise_and(bkg_rgb,bkg_rgb,mask = mask_inv)                 # (2560 , 1440 , 3)
        dst      = cv2.add(img1_bg,con_rgb)                                         # (2560 , 1440 , 3)

        return dst
    '''

    def getLayerInXRay(self,layerNr=0,width=10,scaleDown=2,stack=False,stacklayer=0,progressDialog=None):
        return self.__getLayerInMultiLayerImage(self.__XRAY,  layerNr,scaleDown,stack=stack,stacklayer=stacklayer,progressDialog=progressDialog)
    def getLayerInShaded(self,layerNr=0,width=10,scaleDown=2,stack=False,stacklayer=0,progressDialog=None):
        return self.__getLayerInMultiLayerImage(self.__SHADE,layerNr,scaleDown,stack=stack,stacklayer=stacklayer,progressDialog=progressDialog)
    def __getLayerInMultiLayerImage(self,mode=__XRAY,layerNr=0,scaleDown=2,stack=False,stacklayer=0,progressDialog=None):        
        if mode==self.__XRAY:   multilayerImage=self.getMultiXRay(scaleDown=scaleDown,stack=stack,stacklayer=stacklayer,progressDialog=progressDialog)
        if mode==self.__SHADE:  multilayerImage=self.getMultiShaded(scaleDown=scaleDown,stack=stack,stacklayer=stacklayer,progressDialog=progressDialog)
        bkg_bw  = multilayerImage                                                   # (2560 , 1440 )
        bkg_rgb = cv2.cvtColor(bkg_bw,cv2.COLOR_GRAY2RGB)                           # (2560 , 1440 , 3)
        con_bw  = self.get(layerNr)                                            # (2560 , 1440 )
        if scaleDown!=1:con_bw=cv2.resize(con_bw,(0,0),fx=1/scaleDown,fy=1/scaleDown)
        con_rgb = cv2.cvtColor(con_bw,cv2.COLOR_GRAY2RGB)                           # (2560 , 1440 , 3)
        con_rgb[numpy.where((con_rgb == [255,255,255]).all(axis = 2))] = layerForecolor  # (2560 , 1440 , 3)
        mask     = con_bw
        mask_inv = cv2.bitwise_not(mask)                                            # (2560 , 1440 )
        img1_bg  = cv2.bitwise_and(bkg_rgb,bkg_rgb,mask = mask_inv)                 # (2560 , 1440 , 3)
        dst      = cv2.add(img1_bg,con_rgb)                                         # (2560 , 1440 , 3)

        return dst


    ########################################################################################################################
    ## History methods
    ########################################################################################################################

    # Clipboard Vars to copy/cut and paste layer settinngs/imagedata
    clipboardDef  = None
    clipboardData = None
    History=[]
    HistoryMaxDepth = 10

    def __realDeepCopy(self,dict):
        """ Makes a real copy of a dictionary consisting of bytes strings
        """
        #hC = copy.deepcopy(self.photonfile.Header)
        newDict={}
        for key,byteString in dict.items():
            newDict[key]=(byteString+b'\x00')[:-1] # Force to make a real copy
        return newDict

    def printClipboard(self):
        print ("Clipboard:")
        print ("  Layer height (mm): ",bytes_to_float(self.clipboardDef["Layer height (mm)"]))
        print ("  Exp. time (s)    : ",bytes_to_float(self.clipboardDef["Exp. time (s)"]))
        print ("  Off time (s)     : ",bytes_to_float(self.clipboardDef["Off time (s)"]))
        print ("  Image Address    : ",bytes_to_int(self.clipboardDef["Image Address"]))
        print ("  Data Length      : ",bytes_to_int(self.clipboardDef["Data Length"]))
        print ("  def padding tail : ",len(self.clipboardDef["padding tail"]),"'"+bytes_to_hex(self.clipboardDef["padding tail"])+"'")
        print ("  Raw length)      : ",len(self.clipboardData["Raw"]))
        print ("  Raw padding tail : ",len(self.clipboardData["padding tail"]),"'"+bytes_to_hex(self.clipboardData["padding tail"])+"'")


    def saveToHistory(self, action:str, layerNr:int):
        """ Makes a copy of current /Layer Data to memory
            Since all are bytearrays no Copy.Deepcopy is needed.
        """

        # Copy LayerDefs and LayerData
        layerDef=self.__realDeepCopy(self.LayerDefs[layerNr].copy())
        layerData=self.__realDeepCopy(self.LayerData[layerNr].copy())

        # Append to history stack/array
        newH = {"Action":action,"LayerNr":layerNr,"LayerDef":layerDef,"LayerData":layerData}
        #print("Stored:",id(layerDef),id(layerData))
        self.History.append(newH)
        if len(self.History)>self.HistoryMaxDepth:
            self.History.remove(self.History[0])

        print ("saveToHistory",layerNr,action,">",len(self.History))

    def undo(self):
        # Just an alias
        self.loadFromHistory()

    def loadFromHistory(self):
        """ Load a copy of current Header/Preview/Layer Data to memory
            We copy by reference and remove item from history stack.
        """

        print ("loadFromHistory",">",len(self.History))

        if len(self.History)==0:
            raise Exception("LayerOps.loadFromHistory has reached the maximum depth to undo.")

        # Find last item added to History
        idxLastAdded=len(self.History)-1
        lastItemAdded=self.History[idxLastAdded]
        action=lastItemAdded["Action"]
        layerNr =lastItemAdded["LayerNr"]
        layerDef = lastItemAdded["LayerDef"]
        layerData = lastItemAdded["LayerData"]
        #print("Found:", self.History[idxLastAdded])

        # Reverse the actions
        if action=="insert":
            self.delete(layerNr, saveToHistory=False)
        elif action=="delete":
            self.clipboardDef=layerDef
            self.clipboardData=layerData
            self.insert('clipboard',layerNr, saveToHistory=False)

        # Remove this item
        self.History.remove(lastItemAdded)


    #Make alias for loadFromHistory
    undo = loadFromHistory
        
########################################################################################################################
## Class PhotonFile
########################################################################################################################
    
class PhotonFile: 
    '''
    The following methods are provided to user via PhotonFile interface
    - PhotonFile.convBytes ()
    - PhotonFile.load(filename==None) 
    - PhotonFile.save(filename==None)
    
    - PhotonFile.layers.__headerPropType(propID:str)->int:
    - PhotonFile.layers.setProperty(idString,value)
    - PhotonFile.layers.getProperty(idString)
    
    '''
    
    layers=None
    previews=None
    isDrawing = False # Navigation can call upon retrieving bitmaps frequently. This var prevents multiple almost parallel loads

    Header = {}
    Previews = [{},{}]
    LayerPreviews_padding_tail = b''
    LayerDefs = []
    LayerDefs_padding_tail = b''
    LayerData = []
    LayerDatas_padding_tail = b''

    ########################################################################################################################
    ## Class methods
    ########################################################################################################################

    def __init__(self, photonfilename:str=None):
        """ Just stores photon filename. """
        self.filename = photonfilename

    def __headerPropType(self,propID:str)->int:
        for bTitle, bNr, bType, bEditable,bHint in pfStruct_Header:
            if bTitle==propID:
                return bType

    def signature(self, showPaddingHex=False):
        sign=f'H-{len(self.Header["padding"])}-{len(self.Header["padding tail"])}'
        sign=sign+' / '

        oldsign=''
        for prevNr in range(2):
            newsign=f'{len(self.Previews[prevNr]["padding"])}-{len(self.Previews[prevNr]["padding tail"])}'
            if oldsign!=newsign:
                sign=sign+f'P{prevNr}-{newsign}'
                sign=sign+' / '
                oldsign=newsign

        sign=sign+f'Pt-{len(self.Previews_padding_tail)} / '

        oldsign=''
        for layerNr in range(self.layers.count()):
            newsign=f'{len(self.LayerDefs[layerNr]["padding tail"])}'
            if oldsign!=newsign:
                sign=sign+f'L{layerNr}-{newsign}'
                sign=sign+' / '
                oldsign=newsign

        sign=sign+f'Lt-{len(self.LayerDefs_padding_tail)} / '        

        oldsign=''
        for layerNr in range(self.layers.count()):
            newsign=f'{len(self.LayerData[layerNr]["padding tail"])}'
            if oldsign!=newsign:
                sign=sign+f'D{layerNr}-{newsign}'
                sign=sign+' / '
                oldsign=newsign

        sign=sign+f'Dt-{len(self.LayerDatas_padding_tail)}'        

        if sign in KNOWN_SIGNATURES:
            if self.filename!=None:
                print ("Signature of "+self.filename+" : "+KNOWN_SIGNATURES[sign])
            else:    
                print ("Signature of newfile : "+KNOWN_SIGNATURES[sign])
            return KNOWN_SIGNATURES[sign]

        print ("Signature not found:")
        print (sign)
        
        if not showPaddingHex: return
            
        sign2=f'H-{bytes_to_hex(self.Header["padding"])}-{bytes_to_hex(self.Header["padding tail"])}'
        sign2=sign2+'\n'
        for prevNr in range(2):
            sign2=sign2+f'P{prevNr}-{bytes_to_hex(self.Previews[prevNr]["padding"])}'
            sign2=sign2+'\n'
            sign2=sign2+f'P{prevNr}-{bytes_to_hex(self.Previews[prevNr]["padding tail"])}'
            sign2=sign2+'\n'
        oldsign=''
        for layerNr in range(self.layers.count()):
            newsign=f'{bytes_to_hex(self.LayerDefs[layerNr]["padding tail"])}'
            if oldsign!=newsign:
                sign2=sign2+f'L{layerNr}-{newsign}'
                sign2=sign2+'\n'
                oldsign=newsign
        sign2=sign2+'\n'
        sign2=sign2+f'{bytes_to_hex(self.LayerDefs_padding_tail)}'
        sign2=sign2+'\n'

        oldsign=''
        for layerNr in range(self.layers.count()):
            newsign=f'{bytes_to_hex(self.LayerData[layerNr]["padding tail"])}'
            if oldsign!=newsign:
                sign2=sign2+f'D{layerNr}-{newsign}'
                sign2=sign2+'\n'
                oldsign=newsign
        sign2=sign2+'\n'           
        
        print ("Padding:")
        print (sign2)

        return sign
    

    def getProperty(self,propID:str):
        valbytes = self.Header[propID] 
        valtype  = self.__headerPropType(propID)
        return convBytes(valbytes,valtype)
 
    def setProperty(self,propID:str,value:(int,float)):
        valtype  = self.__headerPropType(propID)
        if (type(value) is int) and valtype==tpInt:
            self.Header[propID] = int_to_bytes(value)
            return
        if (type(value) is float) and valtype==tpFloat:
            self.Header[propID] = float_to_bytes(value)
            return
        raise Exception(f"LayerOps.setProperty got invalid type passed. Property '{propID}' needs {tpTypeNames[valtype]} got {type(value)}.")

    def time(self):
        secs=0
        for lNr in range(0, self.layers.count()):
            exp=bytes_to_float(self.LayerDefs[lNr]["Exp. time (s)"] )
            off=bytes_to_float(self.LayerDefs[lNr]["Off time (s)"] )
            if off<6: off=6
            secs=secs+exp
            secs=secs+off
        return secs    

    def volume(self,retUnit:str='mm3',progressDialog=None)->float:
        """ Returns volume in mm3
        """
        if retUnit not in ('mm3','ml','l'):
            raise Exception(f"PhotonFile.volume received a not allowed retUnit '{retUnit}'.\nAllowed are 'mm3','ml','l'.")

        nLayers=self.layers.count()
        nrPixels=0
        #numpyAvailable=False
        for layerNr in range(0,nLayers):
            rleData=self.layers.get(layerNr,retType='rle')
            pixelsInLayer = RLE.RLEPixels(rleData)

            nrPixels=nrPixels+pixelsInLayer

            # Check if user canceled
            if not progressDialog==None:
                progressDialog.setProgressPerc(100*layerNr/nLayers)
                #progressDialog.setProgressLabel(str(layerNr)+"/"+str(nLayers))
                progressDialog.handleEvents()
                if progressDialog.cancel: return False

        # Calc volume in mm3
        #   1 pixel is 0.047mm x 0.047mm x layer height
        pixVolume=0.047*0.047*bytes_to_float(self.Header["Layer height (mm)"])
        volume=pixVolume*nrPixels       

        # Convert to requested unit
        if retUnit =='mm3': volume=volume
        if retUnit =='ml' : volume=volume/1000.0
        if retUnit =='l'  : volume=volume/1000000.0

        # Round for requested unit
        if retUnit =='mm3': volume=round(volume,0)
        if retUnit =='ml' : volume=round(volume,0)
        if retUnit =='l'  : volume=round(volume,2)

        return volume

    def new(self,signatureName="ACPhotonSlicer"):
        # Load ACPhotonSlicer formatted photon file
        if not os.path.isfile('./newfile.photon'):
            raise Exception ("Installation corrupt, newfile.photon not found in app dir.")

        self.load('./newfile.photon')
        self.filename=None
        set_pfStruct(signatureName)

    def load(self,filename:str=None):
        """ Reads the photofile from disk to memory. """
        self.Header    = {}
        self.Previews  = [{},{}]
        self.Previews_padding_tail = b''
        self.LayerDefs = []
        self.LayerDefs_padding_tail = b''
        self.LayerData = []
        self.LayerDatas_padding_tail = b''
        self.layers=None
        self.previews=None
        
        if not filename==None:
            self.filename=filename
        
        if self.filename==None:
            raise Exception("PhotonFile.load needs a .photon filename on init and in the load method.")

        deb=False

        #if deb: self.filename="/home/nard/PhotonFile/test/bunny.photon"
        if deb: print ("File",self.filename)

        with open(self.filename, "rb") as binary_file:

            # Start at beginning
            binary_file.seek(0)
            idx=0 #keeps file pointer, needed to calc padding lengths

            # Read HEADER / General settings
            if deb: print ("Header",idx)
            for bTitle, bNr, bType, bEditable,bHint in pfStruct_Header:
                # Padding can very and needs to be calculated
                if bTitle=='padding tail':
                    bNr=bytes_to_int( self.Header['Preview 0 (addr)'])-idx
                if bNr>0: 
                    self.Header[bTitle] = binary_file.read(bNr)
                idx=idx+bNr
                if deb: print ("  ",bTitle,bNr," -> ",idx)

            # Read PREVIEWS settings and raw image data
            for previewNr in (0,1):
                if deb: print ("Preview",previewNr,idx)                
                for bTitle, bNr, bType, bEditable, bHint in pfStruct_Previews:
                    # Padding can very and needs to be calculated
                    if bTitle=='padding':
                        bNr=bytes_to_int(self.Previews[previewNr]['Image Address'])-idx
                    if bTitle=='padding tail':
                        if previewNr==0:
                            bNr=bytes_to_int(self.Header['Preview 1 (addr)'])-idx
                        if previewNr==1:
                            bNr=len(self.Previews[0]["padding tail"])

                    # if rawData0 or rawData1 the number bytes to read is given bij dataSize0 and dataSize1
                    if bTitle == "Image Data": bNr = dataSize
                    self.Previews[previewNr][bTitle] = binary_file.read(bNr) if bNr>0 else b''
                    if bTitle == "Data Length": dataSize = bytes_to_int(self.Previews[previewNr][bTitle])
                    idx = idx + bNr
                    if deb: print ("  ",bTitle,bNr," -> ",idx)
            
            # Read PREVIEWS TAIL PADDING
            bNr=bytes_to_int(self.Header['Layer Defs (addr)'])-idx
            self.Previews_padding_tail = binary_file.read(bNr) if bNr>0 else b''
            idx=idx+bNr
 
            # Read LAYERDEFS settings
            nLayers = bytes_to_int(self.Header[nrLayersString])
            self.LayerDefs = [dict() for x in range(nLayers)]
            # print("nLayers:", nLayers)
            # print("  hex:", ' '.join(format(x, '02X') for x in self.Header[self.nrLayersString]))
            # print("  dec:", nLayers)
            # print("Reading layer meta-info")
            if deb: print ("LayerDefs",idx)
            for lNr in range(0, nLayers):
                for bTitle, bNr, bType, bEditable, bHint in pfStruct_LayerDef:
                    self.LayerDefs[lNr][bTitle] = binary_file.read(bNr)
                    idx=idx+bNr

            # read padding between the defs datablock and first image        
            bNr =  bytes_to_int(self.LayerDefs[0]["Image Address"])-idx       
            self.LayerDefs_padding_tail = binary_file.read(bNr) if bNr>0 else b''
            idx=idx+bNr
            
            if deb: print ("LayerDefs padding tail",idx)

            # Read LAYERRAWDATA image data
            if deb: print ("LayerData",idx)
            self.LayerData = [dict() for x in range(nLayers)]
            for lNr in range(0, nLayers):
                rawDataAddr = bytes_to_int(self.LayerDefs[lNr]["Image Address"])
                binary_file.seek(rawDataAddr)

                rawDataSize = bytes_to_int(self.LayerDefs[lNr]["Data Length"])
                # print("  layer: ", lNr, " size: ",rawDataSize)
                self.LayerData[lNr]["Raw"] = binary_file.read(rawDataSize) # b'}}}}}}}}}}
                idx=idx+rawDataSize

                # Read padding between the raw datablocks         
                if lNr<nLayers-1: # Padding between datablocks
                    bNr = bytes_to_int(self.LayerDefs[lNr+1]["Image Address"])-(rawDataAddr+rawDataSize)
                    self.LayerData[lNr]["padding tail"] = binary_file.read(bNr)
                else: # Padding from last datablock to end of file
                    self.LayerData[lNr]["padding tail"] = binary_file.read(-1) 
                    bNr=len(self.LayerData[lNr]["padding tail"])
                idx=idx+bNr
                if deb and bNr>0: print (f"  Layer {lNr} has tail of {bNr} bytes.")

            # correct padding last layer 
            self.LayerDefs_padding_tail = b''
            if nLayers>1:
                lastPaddingBytes = self.LayerData[nLayers-1]["padding tail"]
                prevPaddingBytes = self.LayerData[nLayers-2]["padding tail"]
                lastPaddingLen = len(lastPaddingBytes)
                prevPaddingLen = len(prevPaddingBytes)
                if lastPaddingLen>prevPaddingLen:
                    self.LayerData[nLayers-1]["padding tail"]=lastPaddingBytes[:prevPaddingLen]
                    self.LayerDatas_padding_tail=lastPaddingBytes[prevPaddingLen:]

            if deb:
                print (f"Finished reading {idx} bytes.")
                print (f"File has {os.path.getsize(self.filename)} bytes.")

        # Create new classes with reference to created layerDefs,layerData,Preview
        self.layers   = LayerOps(self,self.LayerDefs,self.LayerData)        
        self.previews = PreviewOps(self,self.Previews)     

        # Set pfStructs
        signatureName = self.signature()
        set_pfStruct(signatureName)   

    def save(self, newfilename:str=None):
        """ Writes the photofile from memory to disk. """

        # Check if other filename is given to save to, otherwise use filename used to load file.
        if newfilename==None:
            if self.filename==None: 
              raise Exception ("New file has no filename yet.")   
            newfilename = self.filename    

        deb=False

        with open(newfilename, "wb") as binary_file:

            # Start at beginning
            binary_file.seek(0)

            # Write HEADER / General settings
            for bTitle, bNr, bType, bEditable,bHint in pfStruct_Header:
                binary_file.write(self.Header[bTitle])
            
            if deb: 
                binary_file.flush()
                print ("Header:",os.path.getsize(newfilename))

            # Write PREVIEWS settings and raw image data
            for previewNr in (0, 1):
                for bTitle, bNr, bType, bEditable, bHint in pfStruct_Previews:
                    binary_file.write(self.Previews[previewNr][bTitle])
            
            binary_file.write(self.Previews_padding_tail)
            
            if deb:
                binary_file.flush()
                print ("Previews:",os.path.getsize(newfilename))

            # Read LAYERDEFS settings
            nLayers = self.layers.count()
            for lNr in range(0, nLayers):
                #print("  layer: ", lNr)
                #print("    def: ", self.LayerDefs[lNr])
                for bTitle, bNr, bType, bEditable, bHint in pfStruct_LayerDef:
                    binary_file.write(self.LayerDefs[lNr][bTitle])

            if deb:
                binary_file.flush()
                print ("LayerDefs:",os.path.getsize(newfilename))

            # Write padding between LAYERDEFS and LAYERDATA (probably 0) 
            binary_file.write(self.LayerDefs_padding_tail)

            # Read LAYERRAWDATA image data
            # print("Reading layer image-info")
            for lNr in range(0, nLayers):
                binary_file.write(self.LayerData[lNr]["Raw"])
                binary_file.write(self.LayerData[lNr]["padding tail"])
                pass

            # Write padding between LAYERDEFS and LAYERDATA (probably 0) 
            binary_file.write(self.LayerDatas_padding_tail)

            if deb:
                binary_file.flush()
                print ("LayerData:",os.path.getsize(newfilename))

   
def main():
    t=time.time()

    #encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION),1]
    img=cv2.imread('/home/nard/PhotonFile/test/3DBenchy.photon-0000.png')
    nr=100
    encimg=None
    for i in range(nr):
        #result, encimg = cv2.imencode('.png', img)
        encimg = cv2.imencode('.png', img)[1]
    decimg = cv2.imdecode(encimg, 1)
    cv2.imwrite(f"/home/nard/PhotonFile/test/comp.png",decimg)
    print (">elapsed",(int(time.time()-t)/nr),len(encimg))    
    #png 0.05 17575
    #jpg 0.04 64431
    return

    photonfile=PhotonFile()    
    photonfile.load('/home/nard/PhotonFile/test/bunny.photon')
    #photonfile.load('/home/nard/PhotonFile/test/3DBenchy.photon')
    #https://docs.opencv.org/3.2.0/d0/d86/tutorial_py_image_arithmetics.html

    #photonfile.layers.getMultiXRay()
    t=time.time()
    nr=1000
    for i in range(nr):
        img=photonfile.layers.getContour(30,1,1)                     #scale/time 2:0.005 sec 1:0.025 sec
        #img=photonfile.layers.getContour(30,15,2)                   #scale/time 2:0.005 sec 1:0.025 sec
        #img=photonfile.layers.getMultiXRay(redraw=True,scaleDown=4) #scale/time 2:2.3   sec 1:6.3       4:1.2 sec
        #img=photonfile.layers.getContourInShaded(30,15,scaleDown=2) #scale/time 1:8.0   sec 2:3.0       4:1.0

    print (">elapsed",(int(time.time()-t)/nr))    
    cv2.imwrite(f"/home/nard/PhotonFile/test/edges.png",img)
    return

    bkg_bw  = photonfile.layers.getMultiXRay()                                    # (2560 , 1440 )
    bkg_rgb = cv2.cvtColor(bkg_bw,cv2.COLOR_GRAY2RGB)                           # (2560 , 1440 , 3)
    con_bw  = photonfile.layers.getContour(30,15)                               # (2560 , 1440 )
    con_rgb = cv2.cvtColor(con_bw,cv2.COLOR_GRAY2RGB)                           # (2560 , 1440 , 3)
    con_rgb[numpy.where((con_rgb == [255,255,255]).all(axis = 2))] = [0,0,255]  # (2560 , 1440 , 3)
    mask     = con_bw
    mask_inv = cv2.bitwise_not(mask)                                            # (2560 , 1440 )
    img1_bg  = cv2.bitwise_and(bkg_rgb,bkg_rgb,mask = mask_inv)                 # (2560 , 1440 , 3)
    dst      = cv2.add(img1_bg,con_rgb)                                         # (2560 , 1440 , 3)

    cv2.imwrite(f"/home/nard/PhotonFile/test/edges.png",dst)

    return

    im=cv2.cvtColor(res,cv2.COLOR_GRAY2RGB)    
    print (im.shape,im)
    im[numpy.where((im == [255,255,255]).all(axis = 2))] = [0,33,166]


    #https://docs.opencv.org/3.2.0/d0/d86/tutorial_py_image_arithmetics.html

    cv2.imwrite(f"/home/nard/PhotonFile/test/edges.png",im)
    
    return
    photonfile=PhotonFile()    
    photonfile.load('/home/nard/PhotonFile/test/3DBenchy.photon')
    #photonfile.load('/home/nard/PhotonFile/test/bunny.photon')
    res=photonfile.layers.getmulti_shaded(False)
    im=cv2.imwrite(f"/home/nard/PhotonFile/test/multilayer_shaded.png",res)
    for brighten in range (10,30,5):
        res=photonfile.layers.getmulti_xray(False,brighten)
        im=cv2.imwrite(f"/home/nard/PhotonFile/test/multilayer_{brighten}.png",res)
    return
    #1
    photonfile=PhotonFile()    
    #photonfile.load('/home/nard/PhotonFile/test/bunny.photon')
    photonfile.new()
    photonfile.layers.insert('/home/nard/PhotonFile/test/bunny.img/0191.png',1)
    photonfile.layers.delete(0,saveToHistory=True)
    photonfile.layers.delete(0,saveToHistory=True)
    photonfile.layers.undo()
    photonfile.layers.undo()
    #photonfile.layers.delete(0)
    photon_filepath_new='/home/nard/PhotonFile/test/all.photon'
    photonfile.save(photon_filepath_new)
    
    return
    #photonfile.new()
    #for i in range(10):
    #photonfile.layers.insert('/home/nard/PhotonFile/test/bunny.img/0191.png',1)
    #photonfile.layers.copy(0,2)
    #photonfile.layers.paste(2)
    photonfile.layers.replaceAll('/home/nard/PhotonFile/test/bunny.img')
    photon_filepath_new='/home/nard/PhotonFile/test/all.photon'
    photonfile.save(photon_filepath_new)
    del photonfile
    return

    photonfile=PhotonFile()    
    photonfile.load('/home/nard/PhotonFile/test/bunny.photon')
    photonfile.layers.delete(photonfile.layers.count())
    photon_filepath_new='/home/nard/PhotonFile/test/del2.photon'
    photonfile.save(photon_filepath_new)
    del photonfile

    photonfile=PhotonFile()    
    photonfile.load('/home/nard/PhotonFile/test/bunny.photon')
    photonfile.layers.delete(800)
    photon_filepath_new='/home/nard/PhotonFile/test/del3.photon'
    photonfile.save(photon_filepath_new)
    del photonfile

    photonfile=PhotonFile()    
    photonfile.load('/home/nard/PhotonFile/test/bunny.photon')
    photonfile.layers.clear()
    photonfile.layers.insert('/home/nard/PhotonFile/test/bunny.img/0050.png',0)
    photon_filepath_new='/home/nard/PhotonFile/test/del4.photon'
    photonfile.save(photon_filepath_new)
    del photonfile

    return

    #en replace all
    photonfile=PhotonFile()    
    photon_filepath_org='/home/nard/PhotonFile/test/bunny.photon'
    photonfile.load(photon_filepath_org)
    print (photonfile.signature())

    photonfile=PhotonFile()    
    photon_filepath_org='/home/nard/PhotonFileEditor-Slicer-v2/SamplePhotonFiles/3DBenchy.photon'
    photonfile.load(photon_filepath_org)
    print (photonfile.signature())

    photonfile=PhotonFile()    
    photon_filepath_org='/home/nard/PhotonFileEditor-Slicer-v2/SamplePhotonFiles/Cube_AS.photon'
    photonfile.load(photon_filepath_org)
    print (photonfile.signature())

    photonfile=PhotonFile()    
    photon_filepath_org='/home/nard/PhotonFileEditor-Slicer-v2/SamplePhotonFiles/Cube_CB.photon'
    photonfile.load(photon_filepath_org)
    print (photonfile.signature())

    photonfile=PhotonFile()    
    photon_filepath_org='/home/nard/PhotonFileEditor-Slicer-v2/SamplePhotonFiles/Hogwarth.photon'
    photonfile.load(photon_filepath_org)
    print (photonfile.signature())

    photonfile=PhotonFile()    
    photon_filepath_org='/home/nard/PhotonFileEditor-Slicer-v2/SamplePhotonFiles/resin-test-25u.B100.2-20.photon'
    photonfile.load(photon_filepath_org)
    print (photonfile.signature())

    photonfile=PhotonFile()    
    photon_filepath_org='/home/nard/PhotonFileEditor-Slicer-v2/SamplePhotonFiles/Smilie.photon'
    photonfile.load(photon_filepath_org)
    print (photonfile.signature())

    return

    #en replace all
    photonfile=PhotonFile()    
    photon_filepath_org='/home/nard/PhotonFile/test/bunny.photon'
    photon_filepath_images='/home/nard/PhotonFile/test/bunny.img'
    photonfile.load(photon_filepath_org)
    #replace from disk
    photonfile.layers.replaceAll(photon_filepath_images)
    photon_filepath_new='/home/nard/PhotonFile/test/bunny_new.photon'
    photonfile.save(photon_filepath_new)
    photonfile.load(photon_filepath_new)
    #replace from rleStack

    return

    print ("Replace All...")
    photonfile=PhotonFile()
    photon_filepath_stack='/home/nard/PhotonFile/test/3DBenchy.photon'
    photonfile.load(photon_filepath_stack)
    rleStack=photonfile.layers.getAll()

    photon_filepath_org='/home/nard/PhotonFile/test/bunny.photon'
    photonfile.load(photon_filepath_org)
    #replace from disk
    photonfile.layers.replaceAll(rleStack)
    #replace from rleStack

    photon_filepath_new='/home/nard/PhotonFile/test/bunny2benchy.photon'
    photonfile.save(photon_filepath_new)
    return

    import sys
    #debug
    sys.argv=('','bunny.photon',)

    if len(sys.argv)==1: return

    path=sys.argv[1].strip()
    
    
if __name__ == '__main__':
    main()