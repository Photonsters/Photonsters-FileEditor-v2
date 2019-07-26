# Shall we call it
#  Photonsters Explorer
#  Photonsters Toolkit?

# some photon files have preview images with w=0 and thus gives error...
# make preview for branch

# TODO:
#   Integrate OpenSlicer in PFE
#   Import PhotonS files
#   Erode on XY plane using contours or erode
#
# ROADMAP:
#   Menu positions: 
#       After check by Photonsters we should fix (tool/menu)bar positions and remove excess bars   
#       Remove these items from prefs dialog
#       Than we can make toolbar for tab0/Preview
#   3d footprint backdrop
#   3d perspective of model or can we implement browser and use Rob's engine?
#   full screen mode for layers?
#   moeten we paddings tussen Header/previews/layerdefs ook laten zien?>
#   kunnen we cv2.contours gebruiken om stls hol te maken?

import os
import sys
import time
import configparser

import tkinter 
import tkinter.ttk as ttk
from tkinter import font
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk

import cv2
import numpy

import PhotonFile 
import ToolTips
import ProgressDialog
import PrefDialog
import ResinDialog

# version
version="1.9 beta"

# colors
colForm='gainsboro'
colButton='light grey'
colButtonActive='gray'
colTreeview="gray30"
layerForecolor=(167,34,252)

# settings
installpath=""
recents=[]
editorscript=['new file...','%1']

# widgets
props=[]
labels=[]
entries=[]
entries_general=[]
entries_previews=[]
entries_layerdefs=[]
lb_PreviewImg=None
lb_LayerImg=None
cbLayerMode=None

# layout of window
root=None
header1=None
header2=None
center=None
left1=None
left2=None
body=None
right1=None
right2=None
tab_parent=None
tab1=None
tab2=None
footer1=None
footer2=None
lbImg=None
slLayerNr1=None
slLayerNr2=None
rootMenu=None
editMenu=None
prevMenu=None
tbEdit=None
tbView=None
tbResin=None
tab1EditIcons=None
tab2EditIcons=None
tab1EditMenuItems=None
tab2EditMenuItems=None

typeMenu=None
modeMenu=None

# toolbars
LEFT='left'
RIGHT='right'
TOP='top'
BOTTOM='bottom'
toolbarConfig={
    'iconbar1':('tab1',TOP),
    'infobar':('tab1',BOTTOM),
    'slider1':('tab1',LEFT),
    'iconbar2':('tab2',TOP),
    'slider2':('tab2',BOTTOM)
}

# navigation counters
prevNr=0
layerNr=0

#####################################################################
## EVENTS
#####################################################################


def keydown(key,mods):
    K_ESC='\x1b'
    if key==K_ESC: root.destroy()

#####################################################################
## MAIN
#####################################################################


def init():
    global installpath
    if getattr(sys, 'frozen', False):# frozen
        installpath = os.path.dirname(sys.executable)
    else: # unfrozen
        installpath = os.path.dirname(os.path.realpath(__file__))
    print ("Installed at: ",installpath)

def readSettings():
    global recents,editorscript,toolbarConfig
    settingsfilepath=os.path.join(installpath,"settings.ini")
    if not os.path.isfile(settingsfilepath): return

    config = configparser.ConfigParser()
    config.read(settingsfilepath)

    try:
        recents=config['DEFAULT']['recents'].split(',')    
        editorscript=config['DEFAULT']['editorscript'].replace('#','%').split(',') 
        toolbarConfig=eval(config['DEFAULT']['toolbars'])
        print ("toolbarConfig",str(toolbarConfig))
    except Exception:
        print (Exception)

def writeSettings():
    global recents,editorscript,toolbarConfig
    settingsfilepath=os.path.join(installpath,"settings.ini")

    config = configparser.ConfigParser()
    config['DEFAULT']['recents'] = ','.join(recents)
    config['DEFAULT']['editorscript']=','.join(editorscript).replace('%','#')
    config['DEFAULT']['toolbars']=str(toolbarConfig)
    with open(settingsfilepath, 'w') as configfile:    # save
        config.write(configfile)


def updateRecents(filename=None):
    global recents
    try:
        for _ in range(5):
            recentMenu.delete(0)
    except:
        pass

    if filename!=None:
        if filename in recents:
            recents.remove(filename)
        recents.insert(0,filename)
    if len(recents)>5: recents=recents[:5]

    for recent in recents:
        recentMenu.add_command(label=recent,command=lambda recent=recent: mnRecent(recent))


##################################################################
####
##################################################################
ind=[None,None]
def createLayerIndicators():
    for tabActive in (0,1):
        sliderName='slider'+str(tabActive+1)
        tab = toolbarConfig[sliderName][0]
        position = toolbarConfig[sliderName][1]
        master = getMasterWidget4Bar(tab, position)
        ind[tabActive]=tkinter.Label(master,text=str(layerNr),bg=master['bg'],width=4,
        #ind[tabActive]=tkinter.Label(master,text=str(layerNr),bg='yellow',width=4,
                                   font=('Helvetica', 8, 'normal'))

def setLayerInd():
    global ind1,ind2,layerNr,slLayerNr1,slLayerNr2
    tabActive = tab_parent.index(tab_parent.select())
    sliderName='slider'+str(tabActive+1)
    tab = toolbarConfig[sliderName][0]
    position = toolbarConfig[sliderName][1]
    master = getMasterWidget4Bar(tab, position)
    #if tabActive==0:
    slLayerNr=slLayerNr1 if tabActive==0 else slLayerNr2

    x,y=slLayerNr.coords()
    #print ("cursor x,y",x,y)
    #print ("widget x y",slLayerNr.winfo_x(),slLayerNr.winfo_y())
    x=x+slLayerNr.winfo_x()
    y=y+slLayerNr.winfo_y()
    if position==TOP   : x,y = x-ind[tabActive].winfo_width()/2,borderSize-slLayerNr.winfo_height()-ind[tabActive].winfo_height()
    if position==BOTTOM: x,y = x-ind[tabActive].winfo_width()/2,slLayerNr.winfo_height()
    if position==LEFT  : x,y = borderSize-slLayerNr.winfo_width()-ind[tabActive].winfo_width(),y-ind[tabActive].winfo_height()/2
    if position==RIGHT : x,y = slLayerNr.winfo_width(),y-ind[tabActive].winfo_height()/2
    #print ("label x,y",x,y)
    #print (slLayerNr2.coords())    
    ind[tabActive].place(x=x,y=y)
    ind[tabActive]["text"]=str(layerNr)
    #ind[tabActive].update_idletasks()

internalSetLayer=False
def setLayer(lNr):
    global layerNr,lbLayerNr,tab_parent,ind,header2,slLayerNr1,slLayerNr2,internalSetLayer
    layerNr=int(lNr)
    lbLayerNr['text'] = str(layerNr)+" / "+str(pf.layers.count())
    
    # Update hidden slLayerNr for new layerNr
    if not internalSetLayer: # prevent callback by slLayerNr widget to this function which is set as its command parameter
        internalSetLayer=True
        slLayerNr1.set(lNr)
        slLayerNr2.set(lNr)
        internalSetLayer=False

    def updateForLayerChange():
        tabActive = tab_parent.index(tab_parent.select())
        if tabActive == 0:
             fillProps('layerdefs')
        if tabActive == 1:
            fillImage()
        setLayerInd()

    # Only update if idle to prevent buildup of events to process
    root.after_idle(updateForLayerChange)

def updateSlLayerNr():
    global slLayerNr1,slLayerNr2,lbNrLayers1,lbNrLayers2,layerNr

    tab1 = toolbarConfig['slider1'][0]
    position1 = toolbarConfig['slider1'][1]
    master1 = getMasterWidget4Bar(tab1, position1)
    tab2 = toolbarConfig['slider2'][0]
    position2 = toolbarConfig['slider2'][1]
    master2 = getMasterWidget4Bar(tab2, position2)

    def updateSlLayer(slLayerNr,tab,position):
        master = getMasterWidget4Bar(tab, position)
        orient='horizontal' if (position == TOP or position == BOTTOM) else 'vertical'
        slLayerNr.grid_forget()
        slLayerNr=tkinter.Scale(master,
                            from_= 0,to=pf.layers.last(),orient = orient,relief="flat",
                            command=setLayer,
                            showvalue=False)
        if position==TOP:st="sew"
        if position==BOTTOM: st="new"
        if position==LEFT:st="ens"
        if position==RIGHT: st="wns"

        if position==TOP or position==BOTTOM:
            slLayerNr.grid(column=1,row=0,sticky=st)
        else:
            slLayerNr.grid(column=0,row=1,sticky=st)
        return slLayerNr

    slLayerNr1=updateSlLayer(slLayerNr1,tab1,position1)
    slLayerNr2=updateSlLayer(slLayerNr2,tab2,position2)

    lbNrLayers1['text']=pf.layers.last()
    lbNrLayers2['text']=pf.layers.last()

    if layerNr>pf.layers.count(): layerNr=pf.layers.last()

def mnNew():
    global root,pf,layerNr
    global slLayerNr,header1,LayerModeBG
    pf.new()
    layerNr=0
    setLayer(0)
    LayerModeBG=None
    updateSlLayerNr()    
    root.title("Photonsters File Editor - new file")
    loadPrevImages()
    fillProps()
    fillFooterWidgets()
    
def mnLoad(filename=None):
    print ("Load")
    global root,pf,layerNr
    global slLayerNr,header1,LayerModeBG
    if filename==None:
        filename =  tkinter.filedialog.askopenfilename(initialdir = ".",title = "Select file",filetypes = (("photon files","*.photon"),("all files","*.*")))
    if not filename: return
    pf.load(filename)
    layerNr=0
    setLayer(0)
    LayerModeBG=None
    updateSlLayerNr()
    updateRecents(filename)
    root.title("Photonsters File Editor - "+os.path.basename(filename))
    loadPrevImages()
    fillProps()
    setBG2Dirty()
    fillImage()
    fillFooterWidgets()


def mnRecent(recent):
    mnLoad(recent)

def mnSave():
    global pf
    mnSaveas(pf.filename)

def mnSaveas(filename=None):
    global oldProp
    global root,pf
    # Check if last entry was valid and if so store it in memory/pf
    if not oldProp==None:
        (old_widget,old_catstr,old_prop,old_action)=oldProp
        ret=editPhotonFileProp(old_widget,old_catstr,old_prop,'enter')    
        if ret==False:
            root.option_add('*Dialog.msg.font', 'Helvetica 10')    
            messagebox.showinfo("Not saved...","File was not saved!")
            return

    # Check if we got a filename
    if filename==None:
        filename =  tkinter.filedialog.asksaveasfilename(initialdir = ".",title = "Select file",filetypes = (("photon files","*.photon"),("all files","*.*")))
    if not filename: return

    # Save file
    pf.save(filename)
    updateRecents(filename)
    pf.filename=filename

    # Set title
    root.title("Photonsters File Editor - "+os.path.basename(pf.filename))

def mnPrefs():
    global root,editorscript,toolbarConfig

    toolbarprefs=[
                toolbarConfig['iconbar1'][1],
                toolbarConfig['slider1'][1],
                toolbarConfig['infobar'][1],
                toolbarConfig['iconbar2'][1],
                toolbarConfig['slider2'][1]
                ]

    sp=PrefDialog.ShowPreferences(root,"Preferences")    
    ret=sp.show(editorscript+toolbarprefs)

    editorscript=ret[:2]
    toolbarprefs=ret[2:]

    toolbarConfig={
    'iconbar1':('tab1',toolbarprefs[0]),
    'slider1':('tab1',toolbarprefs[1]),
    'infobar':('tab1',toolbarprefs[2]),
    'iconbar2':('tab2',toolbarprefs[3]),
    'slider2':('tab2',toolbarprefs[4])
    }

def mnExit():
    writeSettings()
    root.destroy()
    quit()

def mnUndo():
    pf.layers.undo()
    updateSlLayerNr()
    fillProps()

    setBG2Dirty()
    fillImage()

def mnCut():
    pf.layers.delete(layerNr=layerNr,saveToHistory=True)
    updateSlLayerNr()
    fillProps()

    setBG2Dirty()
    fillImage()

def mnCopy():
    pf.layers.copy(layerNr=layerNr,saveToHistory=True)

def mnPaste():
    pf.layers.insert(image='clipboard',layerNr=layerNr,saveToHistory=True)
    updateSlLayerNr()
    fillProps()
    setBG2Dirty()
    fillImage()

def mnExportImg():
    global pf
    dirname =  tkinter.filedialog.askdirectory()
    if not dirname: return

    pf.layers.save(layerNr,dirname)

def mnExportPrev():
    global pf
    dirname =  tkinter.filedialog.askdirectory()
    if not dirname: return

    global prevNr
    filepath=os.path.join(dirname,"prev_"+str(prevNr)+".png")
    pf.previews.save(filepath,prevNr)

def correctImageSize(imagefilename):
    image = cv2.imread(imagefilename,cv2.IMREAD_UNCHANGED)
    # if RGB retrieve Red channel
    if image.ndim==3:
        image=image[:,:,0]
    
    # Check if correct size
    if image.shape != (2560,1440) or image.dtype!=numpy.uint8: # Numpy Array dimensions are switched from PIL.Image dimensions
        root.option_add('*Dialog.msg.font', 'Helvetica 10')    
        messagebox.showerror('Wrong Image Size',
        f'We need an png image with dimensions of 1440x2560 and 8 bit.\n\n'+
        f'Got {image.shape[0]}x{image.shape[1]}x{24 if image.ndim==3 else 8} ({image.dtype})')
        return False
    else:
        return True    

def mnReplaceImg():
    global pf

    filename =  tkinter.filedialog.askopenfilename(
        initialdir = ".",
        title = "Select file",
        filetypes = (("png files","*.png"),)
        )
    if not filename: return

    if correctImageSize(filename):
        pf.layers.load(filename,layerNr,operation='replace')

def mnReplacePrev():
    global pf

    filename =  tkinter.filedialog.askopenfilename(
        initialdir = ".",
        title = "Select file",
        filetypes = (("png files","*.png"),)
        )
    if not filename: return

    global prevNr
    pf.previews.replace(prevNr,filename)
    fillProps()
    loadPrevImages()
    resized()

def mnEditImg():
    import subprocess
    global installpath
    global pf
    global layerNr

    print ("Implement external editor")

    # Export img to tmp
    tmpfilepath = os.path.join(installpath,"tmp.png")
    im=pf.layers.get(layerNr,retType="image-cv2")
    cv2.imwrite(tmpfilepath,im)
    
    # Run editor
    global editorscript
    script=' '.join(editorscript)
    script=script.replace("%1",tmpfilepath)
    print ("run:"+script+"<")
    ret=subprocess.run(script,shell=True) # shell=True so cmd is not searched in current path
    print ("Done")
    
    # Import new image
    if not os.path.isfile(tmpfilepath):
        messagebox.showerror ("Image not found","Image cannot be found. Did you delete it or don't you have write permissions in install directory?")    
        return

    if not correctImageSize(tmpfilepath):
        messagebox.showerror ("Image invalid","Image dimensions and/or depth are not longer the same.")    
        return

    pf.layers.load(tmpfilepath,layerNr,operation='replace')

    setBG2Dirty()
    fillImage()

def mnInsertImg():
    filename =  tkinter.filedialog.askopenfilename(
        initialdir = ".",
        title = "Select file",
        filetypes = (("png files","*.png"),)
        )
    if not filename: return
    if correctImageSize(filename):
        pf.layers.insert(filename,layerNr,saveToHistory=True)

    updateSlLayerNr()
    fillProps()
    setBG2Dirty()
    fillImage()

def mnAppendImg():
    filename =  tkinter.filedialog.askopenfilename(
        initialdir = ".",
        title = "Select file",
        filetypes = (("png files","*.png"),)
        )
    if not filename: return
    if correctImageSize(filename):
        pf.layers.append(filename,saveToHistory=True)

    global layerNr
    updateSlLayerNr()
    layerNr=pf.layers.last()
    fillProps()
    setBG2Dirty()
    fillImage()


def mnReplaceStack():
    global layerNr,root
    dirname =  tkinter.filedialog.askdirectory()
    if not dirname: return
    
    nrFiles = len([f for f in os.listdir(dirname) 
                        if f.endswith('.png') and os.path.isfile(os.path.join(dirname, f))])
    progressDialog=ProgressDialog.showProgress(root,"Importing...",0,nrFiles,autoShow=True,autoHide=False,cancelButton=False)
    pf.layers.replaceAll(dirname,progressDialog)
    layerNr=0
    updateSlLayerNr()    
    setBG2Dirty()
    fillImage()
    fillProps()

def mnExportStack():
    dirname =  tkinter.filedialog.askdirectory()
    if not dirname: return
    if pf.filename==None:
        subdir="newfile"
    else:    
        subdir = os.path.basename(pf.filename)   
        subdir = os.path.splitext(subdir)[0]
    fulldirpath=os.path.join(dirname,subdir)

    # If directory exists warn:
    if os.path.isdir(fulldirpath):
        root.option_add('*Dialog.msg.font', 'Helvetica 10')    
        retOK =  tkinter.messagebox.askokcancel(f"Directory {fulldirpath} already exists.","Do you want to proceed and possibly overwrite existing files?")
        if not retOK: return 
    progressDialog=ProgressDialog.showProgress(root,"Exporting...",0,pf.layers.count(),autoShow=True,autoHide=False,cancelButton=False)
    pf.layers.saveAll(fulldirpath,"",progressDialog)

def mnResins():
    rD=ResinDialog.ResinDialog(root)
    resinVals=rD.show() # 0:Brand 1:Type 2:LayerHeight 3:NormalExposure 
                        # 4:OffTime 5:BottomExposure 6:BottomLayers
    # Replace , in float with . prior to type casting to float
    for i in range(2,6):
        if isinstance(resinVals[i],str):
            resinVals[i]=resinVals[i].replace(",",".")
    print (resinVals)

    # Check if resin profile depends on different layer height
    curLayerHeight=pf.getProperty("Layer height (mm)")
    newLayerHeight=float(resinVals[2])
    if curLayerHeight!=newLayerHeight:
        root.option_add('*Dialog.msg.font', 'Helvetica 10')    
        retOK =  tkinter.messagebox.askokcancel(f"Different Layer Height","This setting depends on a different Layer Height. Do you want to continue?")
        if not retOK: return 

    # Make sure all vars have correct type
    layerHeight=float(resinVals[2])
    expTime=float(resinVals[3])
    offTime=float(resinVals[4])
    expBottom=float(resinVals[5])
    bottomLayers=int(resinVals[6])

    # Set header properties
    pf.setProperty("Layer height (mm)",layerHeight)
    pf.setProperty("Exp. time (s)",expTime)
    pf.setProperty("Off time (s)",offTime)
    pf.setProperty("Exp. bottom (s)",expBottom)
    pf.setProperty("# Bottom Layers",bottomLayers)

    # Set layer properties
    for layerNr in range(pf.layers.count()):
        if layerNr<bottomLayers:
            pf.layers.setProperty(layerNr,"Exp. time (s)",expBottom)
        else:
            pf.layers.setProperty(layerNr,"Exp. time (s)",expTime)
        pf.layers.setProperty(layerNr,"Off time (s)",offTime)

    # Update property labels
    fillProps()

def mnAbout():
    global version
    root.option_add('*Dialog.msg.font', 'Helvetica 10')    
    #https://pythonspot.com/tk-message-box/
    messagebox.showinfo('About', 
    "Version: "+ version +"\n \n Github: PhotonFileUtils \n\n NardJ, X3msnake, Rob2048, \n Antharon, Reonarudo \n \n License: Free for non-commerical use.",                      
    )


##################################################################
####
##################################################################
nrResizes=0
resizing=False
def rootButtonRelease():
    global resizing
    print ("rootButtonRelease")
    if resizing:
        print ("MouseUp")
        resizing=False
        #resized(None)


lastTimerId=-1
oldSize=(0,0)
def resize(arg):
    global lastTimerId,root,oldSize

    # Only resize if size changed
    newSize=(arg.width,arg.height)
    if oldSize==newSize: return
    print (time.time(),"resize",oldSize,newSize,arg)

    # Only resize if size changed > 8 pixels
    if (abs(oldSize[0]-newSize[0])<8 and 
        abs(oldSize[1]-newSize[1])<8    ): return

    if lastTimerId!=-1: root.after_cancel(lastTimerId)
    lastTimerId=root.after(100,resized)

    oldSize=newSize
    pass

lb_PreviewImg = None
def resized():
    global labels
    global entries
    global tab1
    global body,footer1,root
    global lb_PreviewImg
    global lb_LayerImg
    global showPreviewTab1

    print (time.time(),"resized")

    try:
        # Check which tab is active and which widgets to resize/reposition
        tabActive = tab_parent.index(tab_parent.select())

        # If second tab
        if tabActive == 1:
            fillImage()
            return

        # If first tab
        tabheight=tab1.winfo_height()
        dy=props[1].winfo_rooty()-props[0].winfo_rooty()
        if dy<0: return # User is minimizing window too much
        nry=int(tabheight/dy)
        row=0
        col=1
        for prop in props:
            if prop.name=="Category Header": 
                if not (col==0 and row==0):
                    col=col+1
                    row=0     
            #row=nr % nry
            #col=nr //nry
            prop.grid(row=row, column=col)   
            prop.update() 

            if prop.cat=="Previews":
                if type(prop.prop)==list:
                    (bTitle, bNr, bType, bEditable,bHint) = prop.prop
                    if bTitle=="padding tail":
                        if showPreviewTab1.get(): # only reposition if visible
                            xspace = (prop.winfo_width()+12)*2+56 #padx=12 for prop, 56 is fix for some extra margin in columns
                            resizePrevImageForX(xspace)
                            lb_PreviewImg.place(x=prop.winfo_rootx()-tab1.winfo_rootx(),
                                                y=prop.winfo_rooty()-tab1.winfo_rooty()+dy)

            row=row+1
            if row>(nry-1):
                row=0
                col=col+1

        rf=tab1.winfo_height()/2560
        lb_LayerImg['width']=rf*1440
        lb_LayerImg['height']=rf*2560
        lb_LayerImg.update_idletasks()
        setPropLayerImage()

    except Exception as e:
        print ("... ABORT:",e)
 

def createWindow():
    global root
    # setup window
    root = tkinter.Tk()
    root.geometry("%dx%d+0+0" % (640,480))
    root.title("Photonsters File Editor")
    root.name="root"

    iconfilepath=os.path.join(installpath+"/PhotonEditor.png")
    #print("icon",iconfilepath)
    imgicon = tkinter.PhotoImage(file=iconfilepath)
    root.tk.call('wm', 'iconphoto', root._w, imgicon) 

    return root


# setup menu
def createMenu():
    global root,recentMenu,rootMenu,editMenu,viewMenu,typeMenu,modeMenu,prevMenu
    global tab1EditMenuItems,tab2EditMenuItems

    rootMenu=tkinter.Menu(root,relief='flat')
    root.config(menu=rootMenu)

    fileMenu=tkinter.Menu(rootMenu,tearoff=False,relief='flat')
    rootMenu.add_cascade(label="File", menu=fileMenu)
    fileMenu.add_command(label="New",command=mnNew)
    fileMenu.insert_separator(1)
    fileMenu.add_command(label="Load",command=mnLoad)
    recentMenu=tkinter.Menu(fileMenu,tearoff=False,relief='flat')
    recentMenu.add_command(label="recent")
    fileMenu.add_cascade(label="Open Recent", menu=recentMenu)
    fileMenu.insert_separator(5)
    fileMenu.add_command(label="Save",command=mnSave)
    fileMenu.add_command(label="Save As",command=mnSaveas)
    fileMenu.insert_separator(8)
    fileMenu.add_command(label="Preferences",command=mnPrefs)
    fileMenu.insert_separator(10)
    fileMenu.add_command(label="Exit",command=mnExit)

    editMenu=tkinter.Menu(rootMenu,tearoff=False,relief='flat')
    rootMenu.add_cascade(label="Layers", menu=editMenu)
    editMenu.add_command(label="Undo", command=mnUndo)
    editMenu.insert_separator(1)
    editMenu.add_command(label="Cut",command=mnCut)
    editMenu.add_command(label="Copy",command=mnCopy)
    editMenu.add_command(label="Paste",command=mnPaste)
    editMenu.insert_separator(5)
    editMenu.add_command(label="Edit Image",command=mnEditImg)
    editMenu.add_command(label="Insert Image",command=mnInsertImg)
    editMenu.add_command(label="Append Image",command=mnAppendImg)
    editMenu.add_command(label="Replace Image",command=mnReplaceImg)
    editMenu.add_command(label="Export Image",command=mnExportImg)
    editMenu.insert_separator(10)
    editMenu.add_command(label="Replace All",command=mnReplaceStack)
    editMenu.add_command(label="Export All",command=mnExportStack)

    prevMenu=tkinter.Menu(rootMenu,tearoff=False,relief='flat')
    rootMenu.add_cascade(label="Previews", menu=prevMenu)
    prevMenu.add_command(label="Replace Image",command=mnReplacePrev)
    prevMenu.add_command(label="Export Image",command=mnExportPrev)

    resinMenu=tkinter.Menu(rootMenu,tearoff=False,relief='flat')
    rootMenu.add_cascade(label="Resins", menu=resinMenu)
    resinMenu.add_command(label="Change Resin",command=mnResins)

    tab1EditMenuItems=("Undo","Cut","Copy","Paste","Edit Image","Insert Image","Append Image","Replace All","Export All")
    tab2EditMenuItems=("Replace Image","Export Image")

    viewMenu=tkinter.Menu(rootMenu,tearoff=False,relief='flat')
    typeMenu=tkinter.Menu(viewMenu,tearoff=False,relief='flat')
    modeMenu=tkinter.Menu(viewMenu,tearoff=False,relief='flat')

    rootMenu.add_cascade(label="View",  menu=viewMenu)
    viewMenu.add_cascade(label="Type",  menu=typeMenu)
    viewMenu.add_cascade(label="Mode",  menu=modeMenu)
    typeMenu.IV=tkinter.IntVar()
    modeMenu.IV=tkinter.IntVar()
    typeMenu.add_radiobutton(label="None",  command=setViewMenu2Toolbar,variable=typeMenu.IV,value=0)
    typeMenu.add_radiobutton(label="XRay",  command=setViewMenu2Toolbar,variable=typeMenu.IV,value=1)
    typeMenu.add_radiobutton(label="Shade", command=setViewMenu2Toolbar,variable=typeMenu.IV,value=2)
    modeMenu.add_radiobutton(label="All",   command=setViewMenu2Toolbar,variable=modeMenu.IV,value=0)
    modeMenu.add_radiobutton(label="Grow",  command=setViewMenu2Toolbar,variable=modeMenu.IV,value=1)
    viewMenu.add_command(label="Refesh",command=lambda: setBG())

    helpMenu=tkinter.Menu(rootMenu,tearoff=False,relief='flat')
    rootMenu.add_cascade(label="Help", menu=helpMenu)
    helpMenu.add_command(label="About",command=mnAbout)


def setTab2Visible(visible):
    global editMenu,header1,header1,center,footer1,footer2,left1,left2,right1,right2
    global tbEdit,tabs1EditIcons,tabs2EditIcons
    global tab1EditMenuItems,tab2EditMenuItems
    global tbView,viewMenu,tbResin

    print (time.time(),"setTab2Visible")

    if not visible: # TAB 1
        rootMenu.entryconfig('View', state="disabled")
        rootMenu.entryconfig('Previews', state="normal")
        rootMenu.entryconfig('Resins', state="normal")
        
        #for entry in tab1EditMenuItems:
        #    editMenu.entryconfig(entry.title(), state="disabled")
        #for entry in tab1EditIcons:
        #    tbEdit.entryconfig(entry.lower(),state="disabled")    
        for entry in tbView.buttons:
            entry.config(state="disabled")
        for entry in tbResin.buttons:
            entry.config(state="normal")
        #always display header 2
        header1.grid_forget()
        header2.grid(row=0,column=0,sticky="nsew")
        left1.grid(row=0,column=0,sticky="wnse")
        left2.grid_forget()
        right1.grid(row=0,column=2,sticky="ensw")
        right2.grid_forget()
        footer1.grid(row=2,column=0,sticky="snew")
        footer2.grid_forget()

    else:           # TAB 2
        rootMenu.entryconfig('View', state="normal")
        rootMenu.entryconfig('Previews', state="disabled")
        rootMenu.entryconfig('Resins', state="disabled")
        
        #for entry in tab1EditMenuItems:
        #    editMenu.entryconfig(entry.title(), state="normal")
        #for entry in tab1EditIcons:
        #    tbEdit.entryconfig(entry.lower(),state="normal")    
        for entry in tbView.buttons:
            entry.config(state="normal")
        for entry in tbResin.buttons:
            entry.config(state="disabled")

        #always display header 2
        header1.grid_forget()
        header2.grid(row=0,column=0,sticky="nsew")
        left1.grid_forget()
        left2.grid(row=0,column=0,sticky="wnse")
        right1.grid_forget()
        right2.grid(row=0,column=2,sticky="ensw")
        footer1.grid_forget()
        footer2.grid(row=2,column=0,sticky="snew")

        fillImage()
borderSize=46
def createWindowLayout():
    global root, center, body, left1,right1,header1,footer1
    global left2,right2,header2,footer2,tab_parent,tab1,tab2,lbImg
    global borderSize

    root.grid_columnconfigure(0,weight=1)
    root.grid_rowconfigure(0,weight=0)
    root.grid_rowconfigure(1,weight=1)
    root.grid_rowconfigure(2,weight=0)

    debug=False
    defaultbg = root.cget('bg')
    header1 = tkinter.Frame(root,bg='orange red' if debug else defaultbg)#colForm
    header1.name="header1"
    header1.grid(column=0,row=0,sticky="new")

    header2 = tkinter.Frame(root,bg='orange' if debug else defaultbg)#colForm
    header2.name="header2"
    header2.grid(column=1,row=0,sticky="new")
    header2.grid_forget()

    center= tkinter.Frame(root,bg="magenta2" if debug else defaultbg)
    center.name="center"
    center.grid(column=0,row=1,sticky="nesw")

    footer1 = tkinter.Frame(root, bg='deep sky blue' if debug else defaultbg)#colForm
    footer1.name="footer"
    footer1.grid(column=0,row=2,sticky="nesw")

    footer2 = tkinter.Frame(root, bg='sky blue' if debug else defaultbg)#colForm
    footer2.name="footer"
    footer2.grid(column=0,row=2,sticky="nesw")
    footer2.grid_forget()

    # Fix minimal row widths in body
    headerf=tkinter.Frame(root,height=borderSize,width=4,bg="green" if debug else defaultbg)
    headerf.grid(column=1,row=0,sticky="ne")
    centerf=tkinter.Frame(root,width=4,bg="yellow" if debug else defaultbg)
    centerf.grid(column=1,row=1,sticky="nse")
    footerf=tkinter.Frame(root,height=borderSize,width=4,bg="green" if debug else defaultbg)
    footerf.grid(column=1,row=2,sticky="se")

    # Populate center with 3 columns for left,body,right
    center.grid_columnconfigure(0,weight=0)
    center.grid_columnconfigure(1,weight=1)
    center.grid_columnconfigure(2,weight=0)
    center.grid_rowconfigure(0,weight=1)

    left1 = tkinter.Frame(center,bg='spring green' if debug else defaultbg)
    left1.name='left1'

    left2 = tkinter.Frame(center,bg='yellow green' if debug else defaultbg)
    left2.name='left2'

    left1.grid(column=0,row=0,sticky="nsw")
    left2.grid(column=0,row=0,sticky="nsw")
    left2.grid_forget()

    body = tkinter.Frame(center,bg="yellow" if debug else defaultbg)
    body.grid(column=1,row=0,sticky="nesw")
    
    right1 = tkinter.Frame(center,bg='hot pink' if debug else defaultbg)
    right1.name='right1'
    right2 = tkinter.Frame(center,bg='deep pink' if debug else defaultbg)
    right2.name='right2'
    right1.grid(column=2,row=0,sticky="nes")
    right2.grid(column=2,row=0,sticky="nes")
    right2.grid_forget()

    # Fix minimal column widths in body
    leftf=tkinter.Frame(center,width=borderSize,height=4,bg="red" if debug else defaultbg)
    leftf.grid(column=0,row=1,sticky="nw")
    bodyf=tkinter.Frame(center,height=4,bg="yellow" if debug else defaultbg)
    bodyf.grid(column=1,row=1,sticky="new")
    rightf=tkinter.Frame(center,width=borderSize,height=4,bg="red" if debug else defaultbg)
    rightf.grid(column=2,row=1,sticky="ne")

    # If we resize body we need to re-align props
    body.bind("<Configure>", resize)
    body.update()

    # layout of body
    body.grid_columnconfigure(0,weight=1)
    body.grid_rowconfigure(0,weight=1)

    # https://www.homeandlearn.uk/python-database-form-tabs2.html
    tab_parent = ttk.Notebook(body)
    #tab_parent.bind("<<NotebookTabChanged>>",changeTab())

    tab1 = tkinter.Frame(tab_parent)
    tab2 = ttk.Frame(tab_parent)

    tab_parent.add(tab1, text="Properties")
    tab_parent.add(tab2, text="Images")

    tab_parent.pack(expand=1, fill='both')

    tab2.bind("<Visibility>", (lambda _ :setTab2Visible(True))  ) 
    tab1.bind("<Visibility>", (lambda _ :setTab2Visible(False)) )

def createSliderWidgets():
    print ("createSliderWidgets")

    tab1=toolbarConfig['slider1'][0]
    position1=toolbarConfig['slider1'][1]
    master1=getMasterWidget4Bar(tab1,position1)
    tab2=toolbarConfig['slider2'][0]
    position2=toolbarConfig['slider2'][1]
    master2=getMasterWidget4Bar(tab2,position2)

    global slLayerNr1, lbNrLayers1
    global slLayerNr2, lbNrLayers2

    def createSliderWidget(master,position):
        global borderSize
        if position==TOP:st="sew"
        if position==BOTTOM: st="new"
        if position==LEFT:st="ens"
        if position==RIGHT: st="wns"

        if position==TOP or position==BOTTOM:
            master.grid_rowconfigure(0,weight=1)
            lb=tkinter.Label(master,text="0",
                            font=('Helvetica', 8, 'normal'),
                            anchor='e',width=4,padx=4)
            lb.grid(column=0,row=0,sticky=st)
            slLayerNr=tkinter.Scale(master,
                                    from_=0,to=0,orient='horizontal',
                                    relief="flat",
                                    command=setLayer,
                                    showvalue=True)
            slLayerNr.grid(column=1,row=0,sticky=st)
            lbNrLayers=tkinter.Label(master,text="000",
                                    font=('Helvetica', 8, 'normal'),
                                    anchor='w',width=4,padx=4)
            lbNrLayers.grid(column=2,row=0,sticky=st)
            master.grid_columnconfigure(0,weight=0)
            master.grid_columnconfigure(1,weight=1)
            master.grid_columnconfigure(2,weight=0)

        if position==LEFT or position==RIGHT:
            master.grid_columnconfigure(0,weight=1)
            anchor='e' if position==LEFT else 'w'
            lb=tkinter.Label(master,text="0",
                             font=('Helvetica', 8, 'normal'),
                             anchor=anchor,width=4,padx=0)
            lb.grid(column=0,row=0,sticky=st)
            slLayerNr=tkinter.Scale(master,
                                    from_=0,to=0,orient='vertical',
                                    relief="flat",
                                    command=setLayer,
                                    showvalue=False)
            slLayerNr.grid(column=0,row=1,sticky=st)
            lbNrLayers=tkinter.Label(master,text="000",
                                            font=('Helvetica', 8, 'normal'),   
                                            anchor=anchor,width=4,padx=0)
            lbNrLayers.grid(column=0,row=2,sticky=st)
            master.grid_rowconfigure(0,weight=0)
            master.grid_rowconfigure(1,weight=1)
            master.grid_rowconfigure(2,weight=0)
        return slLayerNr,lbNrLayers

    slLayerNr1, lbNrLayers1=createSliderWidget(master1,position1)
    slLayerNr2, lbNrLayers2=createSliderWidget(master2,position2)

def getMasterWidget4Bar(tab,position):
    global header1, footer1, left1, right1
    global header2, footer2, left2, right2

    master=None
    if tab=='tab1': 
        if position==LEFT: master=left1
        if position==RIGHT: master=right1
        if position==TOP: master=header1
        if position==BOTTOM: master=footer1
    if tab=='tab2':
        if position==LEFT: master=left2
        if position==RIGHT: master=right2
        if position==TOP: master=header2
        if position==BOTTOM: master=footer2
    return master

bgType=0
bgMode=0
stbMode=None
stbType=None
def setBG():
    global LayerMode,bgType,bgMode,bgDirty
    if bgType==0: LayerMode=LAYERMODE_PURE
    if bgType==1 and bgMode==0: LayerMode=LAYERMODE_XRAY
    if bgType==2 and bgMode==0: LayerMode=LAYERMODE_SHADE
    if bgType==1 and bgMode==1: LayerMode=LAYERMODE_XRAY_STACK
    if bgType==2 and bgMode==1: LayerMode=LAYERMODE_SHADE_STACK   
    bgDirty=True     
    setLayerMode()
def setBGType(idx):
    global bgType,tbView,stbType
    bgType=idx
    tbView.entryconfig("type",image=stbType.buttons[idx].image)
    global typeMenu
    typeMenu.IV.set(idx)

def setBGMode(idx):
    global bgMode,tbView,stbMode
    bgMode=idx
    tbView.entryconfig("mode",image=stbMode.buttons[idx].image)
    global modeMenu
    modeMenu.IV.set(idx)

def setViewMenu2Toolbar():
    global typeMenu,modeMenu
    global tbView,stbMode,stbType

    tbView.entryconfig("mode",image=stbMode.buttons[modeMenu.IV.get()].image)
    tbView.entryconfig("type",image=stbType.buttons[typeMenu.IV.get()].image)

def createMenuToolbar():
    global tbEdit,tbView,tbResin,stbType,stbMode
    global tab1EditIcons,tab2EditIcons

    tab=toolbarConfig['iconbar2'][0]
    position=toolbarConfig['iconbar2'][1]
    master=getMasterWidget4Bar(tab,position)

    if position==LEFT or position==RIGHT:
        orientationMain=tkinter.VERTICAL
        orientationSub=tkinter.HORIZONTAL
    if position==TOP or position==BOTTOM:
        orientationMain=tkinter.HORIZONTAL
        orientationSub=tkinter.VERTICAL

    ################### TOOLBAR
    from Toolbar import Toolbar
    tbEdit=Toolbar(master,orientation=orientationMain,btnSize=24)
    tbEdit.grid(column=0,row=0,sticky="wns")

    tbEdit.add_command(os.path.join(installpath,"resources/undo.png"),"undo",mnUndo)
    tbEdit.add_command(os.path.join(installpath,"resources/cut.png"),"cut",mnCut)
    tbEdit.add_command(os.path.join(installpath,"resources/copy.png"),"copy",mnCopy)
    tbEdit.add_command(os.path.join(installpath,"resources/paste.png"),"paste",mnPaste)
    tbEdit.add_separator()
    tbEdit.add_command(os.path.join(installpath,"resources/edit.png"),"edit",mnEditImg)
    tbEdit.add_command(os.path.join(installpath,"resources/insert.png"),"insert",mnInsertImg)
    tbEdit.add_command(os.path.join(installpath,"resources/append.png"),"append",mnAppendImg)
    tbEdit.add_command(os.path.join(installpath,"resources/replace.png"),"replace",mnReplaceImg)
    tbEdit.add_command(os.path.join(installpath,"resources/export.png"),"export",mnExportImg)
    tbEdit.add_separator()
    tbEdit.add_command(os.path.join(installpath,"resources/replace_all.png"),"replace *",mnReplaceStack)
    tbEdit.add_command(os.path.join(installpath,"resources/export_all.png"),"export *",mnExportStack)
    tbEdit.add_separator() # Nice seperator to tbView

    tab1EditIcons=('undo','cut','copy','paste','edit','insert','append','replace *','export *')
    tab2EditIcons=('replace','export')

    tbView=Toolbar(master,orientation=orientationMain,btnSize=24)
    if position==LEFT or position==RIGHT:
        tbView.grid(column=0,row=1,sticky="wen")
    else:
        tbView.grid(column=1,row=0,sticky="wns")

    stbType=Toolbar(root,orientation=orientationSub,btnSize=24)
    stbType.add_command(os.path.join(installpath,"resources/bgNone.png"),"none",lambda: setBGType(0))
    stbType.add_command(os.path.join(installpath,"resources/bgXRay.png"),"XRay",lambda: setBGType(1))
    stbType.add_command(os.path.join(installpath,"resources/bgShade.png"),"shade",lambda: setBGType(2))
    tbView.add_cascade(os.path.join(installpath,"resources/bgType.png"),"type",stbType)

    stbMode=Toolbar(root,orientation=orientationSub,btnSize=24)
    stbMode.add_command(os.path.join(installpath,"resources/bgAll.png"),"all",lambda: setBGMode(0))
    stbMode.add_command(os.path.join(installpath,"resources/bgGrow.png"),"grow",lambda: setBGMode(1))
    tbView.add_cascade(os.path.join(installpath,"resources/bgMode.png"),"mode",stbMode)

    tbView.add_command(os.path.join(installpath,"resources/bgCalc.png"),"refresh",lambda: setBG())
    tbView.add_separator() # Nice seperator to tbView

    tbResin=Toolbar(master,orientation=orientationMain,btnSize=24)
    if position==LEFT or position==RIGHT:
        tbResin.grid(column=0,row=2,sticky="wen")
    else:
        tbResin.grid(column=2,row=0,sticky="wns")
    tbResin.add_command(os.path.join(installpath,"resources/resin.png"),"resin",mnResins)


oldProp=None
def tabPhotonFileProp(widget,catstr,prop,action):
    # If we do tab and than mouseselect other field, we need to have this fiel in history
    global oldProp
    oldProp=(widget,catstr,prop,action)

def clickPhotonFileProp(widget,catstr,prop,action):
    global oldProp
    if not oldProp==None:
        (old_widget,old_catstr,old_prop,old_action)=oldProp
        editPhotonFileProp(old_widget,old_catstr,old_prop,"mouseleave")
    oldProp=(widget,catstr,prop,action)

def editPhotonFileProp(widget,catstr,prop,action):
    global layerNr,prevNr,pf
    if catstr=="Header": cat=pf.Header
    if catstr=="Previews": cat=pf.Previews
    if catstr=="LayerDefs": cat=pf.LayerDefs

    (bTitle, bNr, bType, bEditable,bHint)=prop
    print ("Check\n  ",catstr,prop,action)
    if action in ("enter","tab","mouseleave"):
        newVal=widget.get()
        try:
            if bType==PhotonFile.tpFloat:newVal=round(float(newVal),PhotonFile.nrFloatDigits)
            if bType==PhotonFile.tpInt:newVal=int(newVal)
        except ValueError:
            root.option_add('*Dialog.msg.font', 'Helvetica 10')    
            messagebox.showerror("Invalid entry","Non numeric value in field. Please correct and try again.")
            newVal=PhotonFile.convBytes(cat[bTitle],bType) 
            return False
    elif action=="escape":
        newVal=PhotonFile.convBytes(cat[bTitle],bType) 

    widget.delete(0,tkinter.END)
    widget.insert(0,newVal)

    newBytes=PhotonFile.convVal(newVal)  
    if cat==pf.LayerDefs:    
        cat[layerNr][bTitle]=newBytes
    elif cat==pf.Previews:    
        cat[prevNr][bTitle]=newBytes
    else:
        cat[bTitle]=newBytes    

    if action=="escape": return False
    return True

def setPreviewNr(pNr):
    global prevNr
    prevNr=int(pNr)
    fillProps()
    resized() #to update image

def createPropWidgets():
    global entries_general,entries_previews,entries_layerdefs,lb_PreviewImg,lb_LayerImg

    row=0
    def addPropWidgets(cat,prop):
        global props#,row
        nonlocal row

        propFrame=tkinter.Frame(tab1)#,bg=col)
        propFrame.grid(row=row,column=0,padx=12,pady=0,sticky='nsew')
        propFrame.cat=cat
        propFrame.prop=prop

        if type(prop)==str: #label
            propFrame.name="Category Header"
            props.append(propFrame)
            propFrame.columnconfigure(0, weight=0)
            propFrame.columnconfigure(1, weight=1)
            propFrame.columnconfigure(2, weight=0)

            propLabel=tkinter.Label(propFrame,text=prop,font=('Helvetica', 11, 'bold'))#,bg=col)
            propLabel.grid(row=0,column=0,padx=0,pady=0,sticky=tkinter.W+tkinter.W)
            propLabel.name=None

            if prop=="Previews":
                prevNr_IntVar = tkinter.IntVar() 
                lbValue = tkinter.Label(propFrame, anchor="w",textvariable=prevNr_IntVar,
                                        font=('Helvetica', 11, 'bold'))   
                lbValue.grid(row=0,column=1,padx=4,pady=0,sticky=tkinter.E)
                propSelector=tkinter.Scale(propFrame,
                        from_=0,to=1,orient='horizontal',relief="raised",length=6*8,
                        command=lambda prevNr_IntVar=prevNr_IntVar:setPreviewNr(prevNr_IntVar),
                        variable=prevNr_IntVar,
                        showvalue=False)    
                propSelector.grid(row=0,column=2,padx=0,pady=0,sticky=tkinter.E)
            row=row+1

            if prop=="LayerDefs":
                global lbLayerNr
                lbLayerNr = tkinter.Label(propFrame, anchor="e",
                                        font=('Helvetica', 11, 'bold'))   
                lbLayerNr.grid(row=0,column=1,padx=0,pady=0,sticky=tkinter.E)
                lbLayerNrTT=ToolTips.CreateToolTip(lbLayerNr,"Use large scroll above to change layer.")

        else:
            (bTitle, bNr, bType, bEditable,bHint)=prop
            propFrame.name=bTitle
            props.append(propFrame)
            propFrame.columnconfigure(0, weight=1)
            propFrame.columnconfigure(1, weight=1)

            label = tkinter.Label(propFrame, text=bTitle)
            label.grid(row=0,column=0,padx=0,pady=0,sticky=tkinter.W)

            if bEditable: 
                entry = tkinter.Entry(propFrame,width=6,
                highlightcolor='blue')
                entry.bind('<Return>', (lambda _: editPhotonFileProp(entry,cat,prop,'enter')))
                entry.bind('<KP_Enter>', (lambda _: editPhotonFileProp(entry,cat,prop,'enter')))
                entry.bind('<Tab>', (lambda _: editPhotonFileProp(entry,cat,prop,'tab')))
                entry.bind('<FocusIn>', (lambda _: tabPhotonFileProp(entry,cat,prop,'tab')))
                entry.bind('<Button-1>', (lambda _:clickPhotonFileProp(entry,cat,prop,'click')))
                entry.bind('<Escape>', (lambda _: editPhotonFileProp(entry,cat,prop,'escape')))
            else:
                entry = tkinter.Label(propFrame,width=6,anchor="w",relief='sunken',bg=colForm,)
                #entry.config(state=tkinter.DISABLED)

            if len(bHint.strip())>0: # Only add tooltip if we have text to display.
                entryTT=ToolTips.CreateToolTip(entry,bHint)
        
            entry.grid(row=0,column=1,padx=0,pady=0,sticky=tkinter.E)
            entry.bTitle=bTitle
            entry.bType=bType
            entry.bHint=bHint
            row=row+1

            return entry

    addPropWidgets(None,'General')
    for prop in PhotonFile.pfStruct_Header:
        entries_general.append(addPropWidgets("Header",prop))

    addPropWidgets(None,'')
    addPropWidgets(None,'Previews')
    for prop in PhotonFile.pfStruct_Previews:
        entries_previews.append(addPropWidgets("Previews",prop))

    addPropWidgets(None,'')
    addPropWidgets(None,'LayerDefs')
    for prop in PhotonFile.pfStruct_LayerDef:
        entries_layerdefs.append(addPropWidgets("LayerDefs",prop))

    lb_PreviewImg = tkinter.Label(tab1)

    lb_LayerImg = tkinter.Label(tab1,text="layer",width=1,height=1)
    lb_LayerImg.grid(row=0,column=0,sticky=tkinter.N+tkinter.W,rowspan=99)


def createLayerWidgets():
    global tab2,lbImg,cbLayerMode

    lbImg=tkinter.Label(tab2)#, bg="red")#,width=128,height=128)
    lbImg.pack(fill=tkinter.BOTH,expand=True,padx=5,pady=5)#,relief="flat")

showLayerTab1=None
showPreviewTab1=None
resinnames=None
resins=None
def applyResin(arg):
    global cbResin
    cb=cbResin.current()
    print ("applyResin",cb)

def createInfoWidgets():
    #       tab1 - view layer, view preview, signature, print time, volume, resin chooser, 
    #       tab2 - Background selector, nrlayers, nr bottom layers, layerNr, layerheight and cumm layerheight, exp time, off time
    
    global footer1, footer1,footer2,chLayer, chPreview,lbPrinttime,lbVolume,lbSignature
    global showLayerTab1,showPreviewTab1,resinnames,resins
    global cbLayerBackgroundType,cbLayerBackgroundGrow
    global cbResin

    global posInfoTab1,posSliderTab1,posSliderTab2,posIconsTab2
    global header1, footer1, left1, right1

    tab=toolbarConfig['infobar'][0]
    position=toolbarConfig['infobar'][1]
    master=getMasterWidget4Bar(tab,position)
    
    #master=tkinter.Frame(master)
    master.grid(column=0,row=0,sticky="NSEW")
    master.columnconfigure(0,weight=1)

    master.columnconfigure(0,weight=1)
    master.columnconfigure(1,weight=0)
    master.columnconfigure(2,weight=1)
    master.columnconfigure(3,weight=0)
    master.columnconfigure(4,weight=1)

    showLayerTab1=tkinter.BooleanVar(root)
    showPreviewTab1=tkinter.BooleanVar(root)

    chLayer=tkinter.Checkbutton(master,text="Layer image",variable=showLayerTab1,command=togglePropLayerImage)
    chLayer.grid(column=0,row=0,sticky="W")
    chLayer.select()
    
    chPreview=tkinter.Checkbutton(master,text="Preview image",variable=showPreviewTab1,command=togglePropPreviewImage)
    chPreview.grid(column=0,row=1,sticky="W")
    chPreview.select()
    
    sep=ttk.Separator(master,orient=tkinter.VERTICAL)
    sep.grid(column=1,row=0,rowspan=2,sticky="NS",padx=16)

    lbPrinttime=tkinter.Label(master,text="Time: 3 hr, 34 min")    
    lbPrinttime.grid(column=2,row=0,sticky="W")

    lbVolume=tkinter.Label   (master,text="Volume: 52 ml")
    lbVolume.grid(column=2,row=1,sticky="W")

    sep=ttk.Separator(master,orient=tkinter.VERTICAL)
    sep.grid(column=3,row=0,rowspan=2,sticky="NS",padx=16)

    # Add Resin Presets Chooser
    # First read settings from file
    # columns are Brand,Type,Layer,NormalExpTime,OffTime,BottomExp,BottomLayers
    ifile = open("resins.csv", "r",encoding="Latin-1") #Latin-1 handles special characters
    lines = ifile.readlines()
    resins = [tuple(line.strip().split(";")) for line in lines]
    resinnames=[]
    for resin in resins:
        resinnames.append(resin[0]+ "-"+resin[1]+"-"+resin[2])
    cbResin=ttk.Combobox(
                    master, 
                    values=resinnames, 
                    state="readonly", width=20
                    )
    cbResin.grid(column=4,row=0,sticky="EW")    
    cbResin.current(0)
    cbResin.bind("<<ComboboxSelected>>", applyResin)    

    lbSignature=tkinter.Label(master,text="Signature: Anycubic Photon Slicer",width=1,anchor='w')    
    lbSignature.grid(column=4,row=1,sticky="EW")

lbPrinttime=None
lbVolume=None
lbSignature=None

def fillFooterWidgets():
    global lbPrinttime,lbVolume,lbSignature
    if pf!=None: 
        lbSignature['text'] = "ID: "+pf.signature()
        lbVolume   ['text'] = "Vol: "+str(pf.volume(retUnit='ml'))+" ml"
        sec=pf.time()
        timestr=time.strftime('Time: %H:%M:%S', time.gmtime(sec))
        lbPrinttime['text'] = timestr

def loadPrevImages():
    global lb_PreviewImg,pf
    if pf==None: return
    im=pf.previews.get(0,retType="image-cv2")
    im=cv2.rotate(im,cv2.ROTATE_90_CLOCKWISE)    
    image_preview = Image.fromarray(im)
    lb_PreviewImg.Image0 = image_preview

    im=pf.previews.get(1,retType="image-cv2")
    im=cv2.rotate(im,cv2.ROTATE_90_CLOCKWISE)    
    image_preview = Image.fromarray(im)
    lb_PreviewImg.Image1 = image_preview

def resizePrevImageForX(spaceX=128):
    global lb_PreviewImg,prevNr

    #print ("resizePrevImage",prevNr)
    # Retrieve full size image
    if prevNr==0: image_preview = lb_PreviewImg.Image0
    if prevNr==1: image_preview = lb_PreviewImg.Image1

    # Create resized TkImage
    f=spaceX/image_preview.size[0]
    newSize=(int(f*image_preview.size[0]),int(f*image_preview.size[1]))
    image_preview_resized = image_preview.resize(newSize)
    imageTk_preview = ImageTk.PhotoImage(image_preview_resized)

    # Set Image
    lb_PreviewImg['image']= imageTk_preview
    lb_PreviewImg.ImageTk = imageTk_preview

def resizePrevImageForY(spaceY=128):
    global lb_PreviewImg,prevNr

    #print ("resizePrevImage",prevNr)
    # Retrieve full size image
    if prevNr==0: image_preview = lb_PreviewImg.Image0
    if prevNr==1: image_preview = lb_PreviewImg.Image1

    # Create resized TkImage
    f=spaceY/image_preview.size[1]
    newSize=(int(f*image_preview.size[0]),int(f*image_preview.size[1]))
    image_preview_resized = image_preview.resize(newSize)
    imageTk_preview = ImageTk.PhotoImage(image_preview_resized)

    # Set Image
    lb_PreviewImg['image']= imageTk_preview
    lb_PreviewImg.ImageTk = imageTk_preview


def fillProps(group:str='all'):
    global prevNr,layerNr,pf

    def setPropVal(p,val,entry):
        (bTitle, bNr, bType, bEditable,bHint)=p
        val=PhotonFile.convBytes(val,bType)                       
        if type(entry)==tkinter.Entry:
            entry.delete(0, tkinter.END)
            entry.insert(0, val)
        if type(entry)==tkinter.Label:
            entry.config(text=str(val)) 

    if group=='all' or group=='header':
        for entry in entries_general:
            p=PhotonFile.get_pfStructProp(PhotonFile.pfStruct_Header,entry.bTitle)
            val=pf.Header[entry.bTitle] 
            setPropVal(p,val,entry)

    if group=='all' or group=='previews':
        for entry in entries_previews:
            p=PhotonFile.get_pfStructProp(PhotonFile.pfStruct_Previews,entry.bTitle)
            val=pf.Previews[prevNr][entry.bTitle] 
            setPropVal(p,val,entry)

    if group=='all' or group=='layerdefs':
        for entry in entries_layerdefs:
            p=PhotonFile.get_pfStructProp(PhotonFile.pfStruct_LayerDef,entry.bTitle)
            val=pf.LayerDefs[layerNr][entry.bTitle] 
            setPropVal(p,val,entry)
        setPropLayerImage()

def togglePropLayerImage():
    global lb_LayerImg,showLayerTab1
    if showLayerTab1.get():
        lb_LayerImg.grid()
    else:
        lb_LayerImg.grid_remove()
def togglePropPreviewImage():
    global lb_PreviewImg,showPreviewTab1
    if showPreviewTab1.get():
        resized()
    else:
        lb_PreviewImg.place(x=-lb_PreviewImg.winfo_width(),y=0)

def setPropLayerImage():
    global lb_LayerImg,showLayerTab1
    if not showLayerTab1.get(): return # No need to draw anything if not visible
    # Get layer image
    image=pf.layers.get(layerNr,retType='image-cv2')
    # Create resized TkImage
    rf=lb_LayerImg.winfo_height()/2560
    im=cv2.resize(image,(0,0),fx=rf,fy=rf)
    img=Image.fromarray(im)
    photo=ImageTk.PhotoImage(img)
    # Set Image
    lb_LayerImg['image']= photo
    lb_LayerImg.image = photo

bgDirty=True
def setBG2Dirty():
    global bgDirty,LayerMode#,cbLayerBackgroundType,cbLayerBackgroundGrow
    bgDirty=True # force redraw of background
    LayerMode=LAYERMODE_PURE # remove background and wait for user to redraw again
    #cbLayerBackgroundType.current(LAYERMODE_PURE)
    #cbLayerBackgroundGrow.current(LAYERMODE_PURE)

LAYERMODE_PURE=0
LAYERMODE_XRAY=1
LAYERMODE_SHADE=2
LAYERMODE_XRAY_STACK=3
LAYERMODE_SHADE_STACK=4
LayerMode=LAYERMODE_PURE
ScaleDown=1

def setLayerMode():
    fillImage()

def fillImage(arg=None):
    global LayerMode,ScaleDown,bgDirty,layerForecolor  
    global layerNr,lbImg,pf,root,header1,slLayerNr2

    progressDialog=ProgressDialog.showProgress(root,"Calculating...",0,pf.layers.count(),autoShow=False,autoHide=False,cancelButton=False)

    if LayerMode==LAYERMODE_PURE:
        im_bw=pf.layers.get(layerNr,retType="image-cv2")
        im_bw=cv2.rotate(im_bw,cv2.ROTATE_90_CLOCKWISE)
        im_rgb = cv2.cvtColor(im_bw,cv2.COLOR_GRAY2RGB)
        im_rgb[numpy.where((im_rgb == [255,255,255]).all(axis = 2))] = layerForecolor  
        im=im_rgb
    elif LayerMode==LAYERMODE_XRAY:
        im=pf.layers.getLayerInXRay(layerNr,scaleDown=ScaleDown,progressDialog=progressDialog)
        #im=pf.layers.getContourInXRay(layerNr,scaleDown=ScaleDown)
        im = cv2.rotate(im,cv2.ROTATE_90_CLOCKWISE)
    elif LayerMode==LAYERMODE_XRAY_STACK:
        im=pf.layers.getLayerInXRay(layerNr,scaleDown=ScaleDown,stack=True,stacklayer=layerNr,progressDialog=progressDialog)
        #im=pf.layers.getContourInXRay(layerNr,scaleDown=ScaleDown)
        im = cv2.rotate(im,cv2.ROTATE_90_CLOCKWISE)
    elif LayerMode==LAYERMODE_SHADE:
        im=pf.layers.getLayerInShaded(layerNr,scaleDown=ScaleDown,progressDialog=progressDialog)
        #im=pf.layers.getContourInShaded(layerNr,scaleDown=ScaleDown)
        im = cv2.rotate(im,cv2.ROTATE_90_CLOCKWISE)
    elif LayerMode==LAYERMODE_SHADE_STACK:
        im=pf.layers.getLayerInShaded(layerNr,scaleDown=ScaleDown,stack=True,stacklayer=layerNr,progressDialog=progressDialog)
        #im=pf.layers.getContourInShaded(layerNr,scaleDown=ScaleDown)
        im = cv2.rotate(im,cv2.ROTATE_90_CLOCKWISE)
    bgDirty=False

    w=lbImg.winfo_width()
    h=lbImg.winfo_height()
    aspect=2560/1440
    if w/h>aspect: #h is limiting
        rf=h/1440.0
    else:
        rf=w/2560.0
    im=cv2.resize(im,(0,0),fx=rf,fy=rf)
    img=Image.fromarray(im)
    photo=ImageTk.PhotoImage(img)
    lbImg.configure(image=photo)
    lbImg.image = photo
    lbImg.update()
    slLayerNr2.set(layerNr)
    slLayerNr2.update_idletasks()
    #slLayerNr.update()
    return lbImg



init()
readSettings()
createWindow()
createMenu()
updateRecents()
createWindowLayout()
createPropWidgets()
createLayerWidgets()

createMenuToolbar()
createSliderWidgets()
createLayerIndicators()
createInfoWidgets()

pf=PhotonFile.PhotonFile()
mnNew()
root.after(500,resized) # Re align props
root.mainloop()
writeSettings()

'''
# Events: 
#   https://effbot.org/tkinterbook/tkinter-events-and-bindings.htm
#   https://www.python-course.eu/tkinter_events_binds.php
#treeview.bind('<Button-3>',addfav)

root.bind("<ButtonRelease>",mouse_release)
body.bind("<ButtonRelease>",mouse_release)
footer.bind("<ButtonRelease>",mouse_release)
props.bind("<ButtonRelease>",mouse_release)

mods = {
    0x0001: 'Shift',
    0x0002: 'Caps Lock',
    0x0004: 'Control',
    0x0008: 'Left-hand Alt',
    0x0010: 'Num Lock',
    0x0080: 'Right-hand Alt',
    0x0100: 'Mouse button 1',
    0x0200: 'Mouse button 2',
    0x0400: 'Mouse button 3'
}

root.bind( '<Key>', lambda e: keydown( e.char, mods.get( e.state, None )))


'''
