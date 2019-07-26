import time
import numpy
import cv2
import PIL
import PIL.Image

from PhotonFile import *
import RLE

import configparser
config = configparser.ConfigParser()
config.read('TEST.INI')

l=['aaa','sss','ddf','ff']
config['DEFAULT']['path'] = '/var/shared/'    # update
config['DEFAULT']['list'] = ','.join(l)    # update

with open('TEST.INI', 'w') as configfile:    # save
    config.write(configfile)

config.read('TEST.INI')
print (config['DEFAULT']['path'])
print (config['DEFAULT']['list'].split(","))
quit()



def testcases():

    # Test cases
    # read / save photon file
    # read / save cbddlp file (should be same as photon file)

    # read / save properties for header/layers
    # 

    print ("Save All...")
    photon_filepath_org='/home/nard/PhotonFile/test/bunny.photon'
    photonfile=PhotonFile()
    photonfile.load(photon_filepath_org)
    photon_dirpath_new='/home/nard/PhotonFile/test/bunny.img'
    photonfile.layers.saveAll(photon_dirpath_new)
    print("...success.")

    return

    print ("Test signatures...")
    photonfile=PhotonFile()    
    photon_filepath_org='/home/nard/PhotonFile/test/bunny.photon'
    photonfile.load(photon_filepath_org)
    assert (photonfile.signature()=='ChituBox 1.4.0')
    print("...success.")

    print ("Test read/write .cbddlp file...")
    filepath='/home/nard/PhotonFile/test/bunny.cbddlp' 
    filepath_new='/home/nard/PhotonFile/test/bunny2.cbddlp'
    org_filesize=os.path.getsize(filepath)
    photonfile=PhotonFile(filepath)
    photonfile.load()
    photonfile.save(filepath_new)
    new_filesize=os.path.getsize(filepath_new)
    assert new_filesize==org_filesize
    print("...success.")

    print ("Test read/write .photon file...")
    filepath='/home/nard/PhotonFile/test/bunny.photon'
    filepath_new='/home/nard/PhotonFile/test/bunny2.photon'
    org_filesize=os.path.getsize(filepath)
    photonfile=PhotonFile()
    #photonfile.load()
    photonfile.load(filepath)
    photonfile.load(filepath) # do this 2 time to check clear old vars
    photonfile.save(filepath_new)
    new_filesize=os.path.getsize(filepath_new)
    assert new_filesize==org_filesize
    print("...success.")

    print ("Test layers.count / layers.last / layers.height / volume...")
    filepath='/home/nard/PhotonFile/test/bunny.photon'
    photonfile.load(filepath)
    assert photonfile.layers.count() == 1716
    assert photonfile.layers.last() == 1716 -1
    assert photonfile.layers.height(0) == 0.05
    assert photonfile.volume(retUnit='ml') == 9.0
    print("...success.")

    print ("Test Property get/set...")
    dlpWidth_write=2560
    prevWidth_write=320
    layerHeight_write=0.04
    photonfile.setProperty("Resolution X",dlpWidth_write)
    photonfile.previews.setProperty(0,"Resolution X",prevWidth_write)
    photonfile.layers.setProperty(0,"Layer height (mm)",layerHeight_write)
    dlpWidth_read=photonfile.getProperty("Resolution X")
    prevWidth_read=photonfile.previews.getProperty(0,"Resolution X")
    layerHeight_read=photonfile.layers.getProperty(0,"Layer height (mm)")
    assert dlpWidth_read==dlpWidth_write
    assert prevWidth_read==prevWidth_write
    assert layerHeight_read==layerHeight_write
    print("...success.")

    print ("Test layerimage save to file...")
    filepath0='/home/nard/PhotonFile/test/images/test0.png'
    filepath4='/home/nard/PhotonFile/test/images/test4.png'
    photonfile.layers.save(0,filepath0)
    photonfile.layers.save(4,filepath4)
    print("...success.")

    print ("Test image insert to layer...")
    filepath0='/home/nard/PhotonFile/test/images/test0.png'
    filepath4='/home/nard/PhotonFile/test/images/test4.png'
    photonfile.layers.insert(filepath4,4)
    photonfile.layers.insert(filepath0,0)
    assert photonfile.layers.count() == 1716+2
    print("...success.")

    print ("Test layer delete...")
    photonfile.layers.delete(0)
    photonfile.layers.delete(4)
    assert photonfile.layers.count() == 1716
    photonfile.save(filepath_new)
    new_filesize=os.path.getsize(filepath_new)
    assert new_filesize==org_filesize
    print("...success.")

    print ("Test image encoding...")
    filepath = '/home/nard/PhotonFile/test/images/test.png'
    filepath_new='/home/nard/PhotonFile/test/images/test2.png'
    photonfile.layers.insert(filepath,4)
    photonfile.layers.save(4,filepath_new)
    org_imgfilesize=os.path.getsize(filepath)
    org_imgobjsize=PIL.Image.open(filepath).size
    new_imgfilesize=os.path.getsize(filepath_new)
    new_imgobjsize=PIL.Image.open(filepath_new).size
    assert(new_imgobjsize==org_imgobjsize)
    assert(new_imgfilesize==org_imgfilesize)
    print("...success.")

    print ("Test layer replace layer with new image...")
    photon_filepath_org='/home/nard/PhotonFile/test/bunny.photon'
    photonfile.load(photon_filepath_org)
    img_filepath4='/home/nard/PhotonFile/test/images/test4.png'
    photonfile.layers.replace(4,img_filepath4)
    assert photonfile.layers.count() == 1716
    photon_filepath_new='/home/nard/PhotonFile/test/bunny2.photon'
    photonfile.save(photon_filepath_new)
    org_filesize=os.path.getsize(photon_filepath_org)
    new_filesize=os.path.getsize(photon_filepath_new)
    assert new_filesize==org_filesize
    print("...success.")

    print ("Test append photonfile with new image...")
    photon_filepath_org='/home/nard/PhotonFile/test/bunny.photon'
    photon_filepath_new='/home/nard/PhotonFile/test/bunny2.photon'
    photonfile.load(photon_filepath_org)
    img_filepath4='/home/nard/PhotonFile/test/images/test4.png'
    photonfile.layers.append(img_filepath4)
    photonfile.layers.delete(photonfile.layers.last())
    photonfile.save(photon_filepath_new)
    assert new_filesize==org_filesize
    print("...success.")

    print ("Save All...")
    photon_filepath_org='/home/nard/PhotonFile/test/bunny.photon'
    photonfile.load(photon_filepath_org)
    photon_dirpath_new='/home/nard/PhotonFile/test/bunny.img'
    photonfile.layers.saveAll(photon_dirpath_new)
    print("...success.")

    print ("get All...")
    print("...success.")

    print ("Save Replace...")
    print("...success.")

    print ("Test copy image (via clipboard)...")
    print("...success.")

    print ("Test cut/paste image (via clipboard)...")
    print("...success.")

    print ("Test undo (via clipboard)...")
    print("...success.")


    print ("Save Preview...")
    print("...success.")

    print ("Replace Preview...")
    print("...success.")

    return


    #photonfile.exportBitmap(dirPath="/home/nard/PhotonFile/test",filepre="3DB_",layerNr=150)
    #PhotonFile.encodeImageFile2RLE('test/test.png')

    #bmpNp1D=photonfile.getBitmap2(layerNr=150)#,retNumpyArray=True)
    #bmpNp1Duint8=bmpNp1D.flatten().astype(numpy.uint8)
    #print (bmpNp1Duint8.dtype,bmpNp1Duint8.shape,)
    #rle=RLE.encode8bImage2RLE(bmpNp1Duint8)    
    
    #Temp Commented for restruct
    #bmpNp1Duint8=RLE.decodeRLE28bImage(rle)
    #print (bmpNp1Duint8.dtype,bmpNp1Duint8.shape,)
    #img2D=bmpNp1Duint8.reshape(1440,2560)
    #im=PIL.Image.fromarray(img2D)
    #im.save('test/out.png')
    
    #mg=data.reshape(2560,1440,4)
    #        imgarr8=img[:,:,1]
    #        img1D=imgarr8.flatten(0)
    #filename=os.path.abspath('')+"/"+sys.argv[1]
    #filename=sys.argv[1]

    
def main():    
    testcases()
    
if __name__ == '__main__':
    main()