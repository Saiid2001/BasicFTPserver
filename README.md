# FTP Server Project
*EECE 350 final poject*

## Server app
### Running
Go to the location of the project on your machine. and run
```
>>> python server\app.py
```

## Client app
### Requirements

1. Install *matplotlib* library if you don't have it already. Do that by opening the terminal on your machine and running the following command.
```
>>> pip install matplotlib
```

### Running
First make sure the server is running and make note of the IP address of the server. 
Go to the location of the project on your machine. and run
```
>>> python client\app.py
```

A GUI will open up. 
First you have the option to set the ip of the server. Set it to the IP of your server. (if the server is running on the same machine it is the IP of your machine).
Choose the method of FTP connection: either **UDP** or **TCP**

Next, a new window will open up with a file list of available files and the option to download any. You also have the option to upload a file to the FTP server.

Finally you can close the app by hitting the X button. (please note that if you force close the console of the app, a connection issue might occure because of incomplete closing).


## Deliverables
1. Both sending and receiving rates and averages are visible. For the client you can see it in the plot at the end or in the console or besides the progress bar throughout. For the server it is shown in the console log of the app throughout the process.

