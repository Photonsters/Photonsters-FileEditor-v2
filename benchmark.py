import time
import numpy
import cv2
import PIL
import PIL.Image

from PhotonFile import *
import RLE

def benchmarks():

    print ("BENCHMARK...")
    photonfilepath='/home/nard/PhotonFile/test/bunny.cbddlp' 
    photonfile=PhotonFile(photonfilepath)
    photonfile.load()
    n=50

    print ()
    print (" UNITS...")

    #PIL.Image.open
    imgfilepath='/home/nard/PhotonFile/test/images/test.png' 
    t=time.time()
    for i in range(0,n): 
        im=PIL.Image.open(imgfilepath)
        nparr=numpy.asarray(im) 
    d=(time.time()-t)/n
    print (f"  PIL.Image.open x 1000        : {round(1000*d,2)} sec")

    #cv2.imread
    imgfilepath='/home/nard/PhotonFile/test/images/test.png' 
    t=time.time()
    for i in range(0,n): 
        im=cv2.imread(imgfilepath)
        nparr=im
    d=(time.time()-t)/n
    print (f"  cv2.imread x 1000            : {round(1000*d,2)} sec")

    #PIL.Image.save (comp level = 3 is fastest)
    imgfilepath='/home/nard/PhotonFile/test/images/test.png' 
    imgfilepath_new='/home/nard/PhotonFile/test/images/test_save2pil.png' 
    im=PIL.Image.open(imgfilepath)
    t=time.time()
    for i in range(0,n): im.save(imgfilepath_new,compress_level=3)
    d=(time.time()-t)/n
    print (f"  PIL.Image.save(comp=6) x 1000: {round(1000*d,2)} sec")

    #CV.imwrite
    imgfilepath='/home/nard/PhotonFile/test/images/test.png' 
    imgfilepath_new='/home/nard/PhotonFile/test/images/test_save2cv2.png' 
    img = cv2.imread(imgfilepath,-1)
    t=time.time()
    for i in range(0,n): 
        cv2.imwrite(imgfilepath_new,img)
        #cv2.imwrite(imgfilepath_new,img,[int(cv2.IMWRITE_PNG_COMPRESSION), 1])
    d=(time.time()-t)/n
    print (f"  CV2.Image.write x 1000       : {round(1000*d,2)} sec")

    #PIL.Image -> Numpy 1D
    t=time.time()
    for i in range(0,n): 
        np=numpy.asarray(im)
        if np.ndim==3: np=np[:,:,0]
        npf=np.flatten()
    d=(time.time()-t)/n
    print (f"  PIL.Image -> Numpy 1D x 1000 : {round(1000*d,2)} sec")

    #cv2.Image -> Numpy 1D
    t=time.time()
    for i in range(0,n): 
        np=numpy.array(img)
        if np.ndim==3: np=np[:,:,0]
        npf=np.flatten()
    d=(time.time()-t)/n
    print (f"  CV2.Image -> Numpy 1D x 1000 : {round(1000*d,2)} sec")

    #decodeRLE
    rleData=photonfile.layers.get(3,retType='rle')
    t=time.time()
    for i in range(0,n): nparr=RLE.decodeRLE28bImage(rleData)
    d=(time.time()-t)/n
    print (f"  RLE.decodeRLE28bImage x 1000 : {round(1000*d,2)} sec")

    #encodeRLE
    t=time.time()
    for i in range(0,n): rleData=RLE.encode8bImage2RLE(npf)
    d=(time.time()-t)/n
    print (f"  RLE.encode8bImage2RLE x 1000 : {round(1000*d,2)} sec")

    #get nrpixels
    rleData=photonfile.layers.get(4,retType='rle')
    t=time.time()
    for i in range(0,n): pixelsInLayer=RLE.RLEPixels(rleData)
    d=(time.time()-t)/n
    print (f"  RLE.RLEPixels x 1000         : {round(1000*d,2)} sec")

    #get rle bytes
    t=time.time()
    for i in range(0,n): rleData=photonfile.layers.get(4,'rle')
    d=(time.time()-t)/n
    print (f"  layers.get(4,'rle') x 1000   : {round(1000*d,2)} sec")

    #get numpy bytes
    t=time.time()
    for i in range(0,n): numpy2D=photonfile.layers.get(4,retType='numpy')
    d=(time.time()-t)/n
    print (f"  layers.get(4,'numpy') x 1000 : {round(1000*d,2)} sec")

    #get volume
    t=time.time()
    for i in range(0,n): numpy2D=photonfile.volume()
    d=(time.time()-t)/n
    print (f"  photonfile.volume() x 1      : {round(d,2)} sec")

    print ()
    print (" EXPORT/IMPORT...")

    #export image from rle data in layer using PIL.Image.save
    imgfilepath_new='/home/nard/PhotonFile/test/images/test_export2pil.png'
    t=time.time()
    for i in range(0,n): 
        rleData=photonfile.layers.get(3,retType='rle')
        numpyArray1Duint8=RLE.decodeRLE28bImage(rleData)
        numpyArray2Duint8=numpyArray1Duint8.reshape(2560,1440)
        im=PIL.Image.fromarray(numpyArray2Duint8)
        im.save(imgfilepath_new,compress_level=3)
    d=(time.time()-t)/n
    print (f"  RLE->PIL.Image.save x 1000   : {round(1000*d,2)} sec")

    #export image from rle data in layer using CV2.imwrite
    imgfilepath_new='/home/nard/PhotonFile/test/images/test_export2cv2.png'
    t=time.time()
    for i in range(0,n): 
        rleData=photonfile.layers.get(3,retType='rle')
        numpyArray1Duint8=RLE.decodeRLE28bImage(rleData)
        numpyArray2Duint8=numpyArray1Duint8.reshape(2560,1440,1)
        cv2.imwrite(imgfilepath_new,numpyArray2Duint8)
    d=(time.time()-t)/n
    print (f"  RLE->CV2.Image.write x 1000  : {round(1000*d,2)} sec")

    #import image from rle data in layer using PIL.Image.open
    imgfilepath_new='/home/nard/PhotonFile/test/images/test.png'
    t=time.time()
    for i in range(0,n): 
        im=PIL.Image.open(imgfilepath_new)
        npArray=numpy.asarray(im)
        if npArray.ndim==3:
            npArray=npArray[:,:,0]
        npArray=npArray.flatten()
        rleData=RLE.encode8bImage2RLE(npArray)
    d=(time.time()-t)/n
    imgfilepath_chk='/home/nard/PhotonFile/test/images/test_checkload_pil.png'
    numpyArray1Duint8=RLE.decodeRLE28bImage(rleData)
    numpyArray2Duint8=numpyArray1Duint8.reshape(2560,1440)
    im=PIL.Image.fromarray(numpyArray2Duint8)
    im.save(imgfilepath_chk,compress_level=3)    
    print (f"  PIL.Image.open->RLE x 1000   : {round(1000*d,2)} sec")

    #import image from rle data in layer using CV2.imread
    imgfilepath_new='/home/nard/PhotonFile/test/images/test.png'
    t=time.time()
    for i in range(0,n): 
        npArray=cv2.imread(imgfilepath_new,cv2.IMREAD_UNCHANGED) # is native numpy array
        if npArray.ndim==3:
            npArray=npArray[:,:,0]
        npArray=npArray.flatten()
        rleData=RLE.encode8bImage2RLE(npArray)
    d=(time.time()-t)/n
    imgfilepath_chk='/home/nard/PhotonFile/test/images/test_checkload_cv2.png'
    numpyArray1Duint8=RLE.decodeRLE28bImage(rleData)
    numpyArray2Duint8=numpyArray1Duint8.reshape(2560,1440,1)
    cv2.imwrite(imgfilepath_chk,numpyArray2Duint8)
    print (f"  CV2.imread->RLE x 1000       : {round(1000*d,2)} sec")

def main():    
    benchmarks()
    #testcases()
    
if __name__ == '__main__':
    main()