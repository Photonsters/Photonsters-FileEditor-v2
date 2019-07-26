import tkinter as tk
import tkinter.ttk as ttk
from tkinter import font
from PIL import Image, ImageTk

class Toolbar(tk.Frame):
    buttons=[]
    buttonImgs=[]
    buttonLabels=[]
    isCascade=False
    visible=True

    def __init__(self,master,orientation=tk.HORIZONTAL,btnSize=22,font=None,**kw):
        super().__init__(master,kw)
        self.orientation=orientation
        self.btnSize=btnSize
        if font==None:
            font = tk.font.Font(family='Helvetica', size=8, weight='bold')
        self.btnFont=font
        if not 'bg' in kw and master['bg']!='': 
            self['bg']=master['bg']

        self.buttonNr=0
        self.buttons=[]
        return
        if orientation==tk.HORIZONTAL:
            self['width']=btnSize
        if orientation==tk.VERTICAL:
            self['height']=btnSize

    def add_command(self,imagefilepath,text:str,command=None,subToolbar=None):
        im = Image.open(imagefilepath)
        w=self.btnSize
        h=self.btnSize+self.btnFont['size']
        margin=3
        im = im.resize((w, w), Image.ANTIALIAS)
        tkimage = ImageTk.PhotoImage(im)
        btnTool = tk.Button(self, 
                                text=text, image=tkimage, 
                                compound="top",
                                relief='flat',
                                bg=self['bg'],
                                width=w,height=h,
                                pady=margin,padx=margin+self.btnFont['size']/2,
                                command=command)
        btnTool['font'] = self.btnFont
        btnTool.image=tkimage
        btnTool.bind("<Button-1>", self.mousebutton)
        btnTool.command=command
        btnTool.toolbar=subToolbar
        btnTool.index=self.buttonNr
        if self.orientation==tk.VERTICAL:
            btnTool.grid(column=0,row=self.buttonNr)
        else:    
            btnTool.grid(column=self.buttonNr,row=0)
        self.buttonNr=self.buttonNr+1

        self.buttons.append(btnTool)
        return btnTool

    def add_cascade(self,imagefilepath,text:str,toolbar):
        if self.isCascade:
            raise Exception("Cascaded toolbars can not be assigned cascaded toolbars.")
        toolbar.isCascade=True
        toolbar.visible=False
        toolbar.master=self._nametowidget('.') # reset master to root window
        toolbar['relief']='groove'
        toolbar['borderwidth']=1

        return self.add_command(imagefilepath,text,subToolbar=toolbar)

    def add_separator(self,pad=4):
        if self.orientation==tk.HORIZONTAL:        
            sep=ttk.Separator(self,orient=tk.VERTICAL)
            sep.grid(column=self.buttonNr,row=0,sticky="NS",padx=pad)
        if self.orientation==tk.VERTICAL:        
            sep=ttk.Separator(self,orient=tk.HORIZONTAL)
            sep.grid(column=0,row=self.buttonNr,sticky="EW",pady=pad)
        self.buttonNr=self.buttonNr+1
        return sep

    def entryconfig(self,index,**kw):
        for button in self.buttons:
            label=button['text']
            if label==index:
                button.config(kw)
                return

        labels=[button['text'] for button in self.buttons]
        raise Exception("Index not found. Present indices: "+str(labels))

    def mousebutton(self,event):
        button=event.widget
            
        # If this is SUB toolbar
        if self.isCascade:
            print("Sub Button",event.widget['text'])            
            self.place_forget()
            self.visible=False
            button.command()#button.index)
            return

        # If this is MAIN toolbar
        else: # So we are root   
            # Check if already visible
            button=event.widget
            if button.toolbar!=None:
                if button.toolbar.visible:
                    button.toolbar.visible=False
                    button.toolbar.place_forget()
                    return                    

            # Hide all other subtoolbars
            for button in self.buttons:
                subtoolbar=button.toolbar
                if subtoolbar!=None:
                    subtoolbar.place_forget()
                    subtoolbar.visible=False
                                        
            # if button has subtoolbar we display it
            button=event.widget
            subtoolbar=button.toolbar
            button.subvisible=True
            if subtoolbar!=None:
                root=self._nametowidget('.')
                x=button.winfo_x()#+button.winfo_width()
                y=button.winfo_y()+button.winfo_height()

                button_x_in_window=button.winfo_rootx()-root.winfo_x()
                button_y_in_window=button.winfo_rooty()-root.winfo_y()
                window_width=root.winfo_width()
                window_height=root.winfo_height()
                subtoolbar_width=subtoolbar.winfo_reqwidth()
                subtoolbar_height=subtoolbar.winfo_reqheight()
                #print (subtoolbar.orientation)
                #print (button_x_in_window,window_width,subtoolbar_width)
                #print (button.winfo_rootx()-root.winfo_x(),root.winfo_width())
                if self.orientation==tk.VERTICAL:
                    if window_width-button_x_in_window<subtoolbar_width:
                        subtoolbar.place(x=button_x_in_window-subtoolbar.winfo_reqwidth(),  
                                         y=button_y_in_window)                
                    else:
                        subtoolbar.place(x=button.winfo_x()+button.winfo_width(),
                                         y=button_y_in_window)                
                if self.orientation==tk.HORIZONTAL:
                    if window_height-button_y_in_window<subtoolbar.winfo_reqheight():
                        subtoolbar.place(x=button_x_in_window,
                                           y=button_y_in_window-subtoolbar.winfo_reqheight())
                    else:
                        subtoolbar.place(x=button_x_in_window,
                                           y=button.winfo_y()+button.winfo_height())                

                subtoolbar.visible=True
            else:
                print("Main button",button['text'])  
                        
if __name__ == '__main__':
    import PhotonFileEditor