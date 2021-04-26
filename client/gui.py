# code for gui written by Saiid El Hajj Chehade

# code references:
# https://realpython.com/python-gui-tkinter
# https://stackoverflow.com/questions/111155/how-do-i-handle-the-window-close-event-in-tkinter
# https://www.tutorialspoint.com/progressbar-widget-in-python-tkinter

import tkinter as tk
from tkinter import HORIZONTAL
from tkinter import filedialog as fd
from tkinter.ttk import Progressbar
from connections.mainConnection import MainConnection
import os
from config import SERVER_IP

connection = None


# the window related to choosing the ip and the connection method
def connectionPrompt():
    mainWindow = tk.Tk()

    frm_ip = tk.Frame()

    lbl_ip = tk.Label(text='Choose FTP server IP:', master=frm_ip)
    lbl_ip.pack(fill=tk.Y, side=tk.LEFT)

    ent_ip = tk.Entry(master=frm_ip)
    ent_ip.pack(fill=tk.Y, side=tk.LEFT)

    frm_ip.pack(fill=tk.X)

    frm_conn = tk.Frame()
    lbl_conn = tk.Label(text='Choose FTP connection method:', master=frm_conn)
    lbl_conn.pack(fill=tk.Y, side=tk.LEFT)

    def connect():
        return MainConnection(server_ip=ent_ip.get())

    # display error in window
    def showError(error):
        lbl_warning['text'] = error

    # button action for udp button
    def chooseUDP():

        # if ip value is entered
        if ent_ip.get().strip():
            conn = connect()
            conn = conn.connectFTP('UDP')
            mainWindow.destroy()
            fileWindow(conn)
        else:
            showError("Empty IP")

    # button action for tcp button
    def chooseTCP():
        if ent_ip.get().strip():
            conn = connect()
            conn = conn.connectFTP('TCP')
            mainWindow.destroy()
            fileWindow(conn)
        else:
            showError("Empty IP")

    btn_tcp = tk.Button(
        text='TCP',
        master=frm_conn,
        command=chooseTCP
    )
    btn_tcp.pack(fill=tk.Y, side=tk.LEFT)
    btn_udp = tk.Button(
        text='UDP',
        master=frm_conn,
        command=chooseUDP
    )
    btn_udp.pack(fill=tk.Y, side=tk.LEFT)

    frm_conn.pack(fill=tk.X)

    lbl_warning = tk.Label(foreground='RED')
    lbl_warning.pack()
    mainWindow.mainloop()


import time
# contribution from https://www.geeksforgeeks.org/how-to-embed-matplotlib-charts-in-tkinter-gui/
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)


# the file window that deals with the file list, downloading and uploading files
def fileWindow(connection):
    # get the file list from the server
    fileList = connection.getFiles()

    window = tk.Tk()

    lbl_files = tk.Label(text='Files on Server')
    lbl_files.pack()

    frm_main = tk.Frame()
    frm_files = tk.Frame(master=frm_main)
    frm_plot = tk.Frame()
    frm_progress = tk.Frame(master=frm_main)

    lbl_progress = tk.Label(master=frm_progress)

    # a progress bar to show upload or download progress
    progressBar = Progressbar(frm_progress, orient=HORIZONTAL, length=200, mode='determinate')

    lbl_rate = tk.Label(master=frm_progress)

    # values for realtime bitrate for receiving rates and throughput while sending
    X = []
    Y = []

    # script to run when a new segment of data is received or sent
    def progress(done, total, bitrate):
        """

        :param done: the number of completed segments
        :param total: total number of segments
        :param bitrate
        :return:
        """
        global fileList

        fraction = total // 30
        # update progress only if we move by a fraction of total
        if fraction == 0 or done % fraction == 0 or done == total:

            # add bitrate values
            X.append(time.perf_counter_ns() / 1E9)
            Y.append(bitrate)

            # update progress bar
            progressBar['value'] = done * 1.0 / total * 100.0

            # update rate text
            lbl_rate['text'] = f'{round(bitrate)} bits/s'

            # if the process ended
            if done == total:

                lbl_progress['text'] = "Finished"
                lbl_rate['text'] = f'Average {round(bitrate)} bits/s'

                # plot the bitrate throughout the process
                fig = Figure(figsize=(5, 5),
                             dpi=100)
                fig.clear()
                plot1 = fig.add_subplot(111)
                fig.supylabel('Bitrate (bps)')
                fig.supxlabel('timestamp (s)')
                plot1.plot(X, Y)

                for child in frm_plot.children:
                    frm_plot.children[child].destroy()
                    break

                canvas = FigureCanvasTkAgg(fig,
                                           master=frm_plot)
                canvas.draw()

                X.clear()
                Y.clear()

                # get the new file list in case an upload occured
                fileList = connection.getFiles()

                # re draw the gui for the file list
                showFiles(fileList)

                # placing the canvas on the Tkinter window
                canvas.get_tk_widget().pack()
            window.update_idletasks()

    # script for showing the file list entries on server
    def showFiles(fileList):

        for i in range(len(fileList)):
            frm_files.columnconfigure(i, weight=1, minsize=75)
            frm_files.rowconfigure(i, weight=1, minsize=50)

            frame = tk.Frame(
                master=frm_files,
                borderwidth=1
            )
            frame.grid(row=i, column=0, padx=5, pady=5)

            label = tk.Label(master=frame, text=fileList[i]['file'])
            label.pack(padx=5, pady=5)

            frame = tk.Frame(
                master=frm_files,
                borderwidth=1
            )
            frame.grid(row=i, column=1, padx=5, pady=5)

            # script to run when download button is pressed
            def download(i):
                lbl_progress['text'] = "Downloading " + fileList[i]['file']
                window.update_idletasks()

                # open file dialog to select directory
                path = fd.askdirectory()
                if len(path) < 2: return

                connection.downloadFile(fileList[i]['id'], path, log=progress)

            btn = tk.Button(
                master=frame,
                text='Download',
                command=lambda a=i: download(a)
            )
            btn.pack(padx=5, pady=5)

    showFiles(fileList)

    frm_main.pack(side=tk.LEFT)
    frm_files.pack()
    frm_plot.pack(side=tk.RIGHT)
    lbl_progress.pack(fill=tk.Y, side=tk.LEFT)
    progressBar.pack(fill=tk.Y, side=tk.LEFT)
    lbl_rate.pack(fill=tk.Y, side=tk.LEFT)
    frm_progress.pack()

    # script to run when upload button is pressed
    def upload():

        # open file dialog
        path = fd.askopenfilename()

        if len(path) < 2: return

        path = os.path.normpath(path)
        *directory, filename = path.split(os.sep)
        directory = os.sep.join(directory)
        *filename, filetype = filename.split('.')
        filename = '.'.join(filename)
        
        lbl_progress['text'] = "Uploading " + filename + "." + filetype

        window.update_idletasks()

        connection.sendFile(directory, filename, filetype, log=progress)

    btn = tk.Button(
        text='Upload',
        command=upload,
        master=frm_progress
    )
    btn.pack(padx=5, pady=5)

    def on_close():
        # if connection udp
        connection.close()
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_close)
    window.mainloop()
