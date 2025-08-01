The purpose of the App is to act like a github for 3d printing, but with the focus of data tracking. To track changes to parameters and correlate them with print outcomes. 
The app should also have the ability to log things like physical printer malfunctions. In the end I would like a timeline of a printers life with print files, maintenance, and print parameters being tracked over time. 

Desired behavior: 

- the app should display a "log book" of printed files and maintenance. when clicked on any of these elements it should take the user to a page where all the print parameters or details can be viewed more clearly

- when a gcode file is uploaded to my 3d printer i want a copy of that gcode to be stored in a running database of prints 

- the app should monitor the klipper/moonraker API for the status of that specific print. If the print is cancelled by the user, or if it is successful this should be noted 

- on the print end behavior (either a cancellation or a success) the user should be prompted to enter some quick information about the print.
        - this information will be the print quality on a scale of 1-10
        - the print functionality on a scale of 1-10
        - the ability to give the print a label: "structural", "fluidic", "test", etc.
        - the ambient room temperature
        - the ambient humidity 
        - and any other notes 
        - and whether or not the print was a success 

- when a gcode file is saved as many possible slicer parameters should be analyzed and tracked. 
        - parameter changes should be tracked relative to the previous print and highlighted. for example, if the previous print had 0.96 extrusion multiplier and this is changed to 1. this should be highlighted as a change from the current print to the previous print 

- notable features of the printed part should also be recorded.
        - dimensions of the part
        - bridging distance
        - number of holes etc. 

- There should be the ability to add maintenance events to the log book list. 
        - this will have a description of the printer maintenance that was done
        - the date and time this occured 
        - and any outstanding to do tasks resulting from it


- A visual graph representation or "printer timeline" that shows the logbook events 
