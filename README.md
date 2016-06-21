# spe2py

spe2py is a module that imports a Princeton Instruments LightField (SPE 3.x) file into a python environment. 

### Basic Usage
##### Loading and accessing data
Use the `load()` function to load one or more SPE files at a time:
```python
>>> import spe2py as spe
>>> loaded_files = spe.load()
```
A file selection window will open to allow browsing for source files. The result is an individual SpeFile object, or, in the case where multiple files are loaded at once, a list of SpeFile objects.

Raw data from a file is stored in NumPy arrays and can be accessed directly by
```python
>>> frame_data = loaded_files.data[frame][regionOfInterest]  
>>> frame_data = loaded_files[n].data[frame][regionOfInterest]  # where multiple files are loaded
```
Alternatively one can load an individual file by passing `SpeFile()` the source path directly:
```python
file_object = spe.SpeFile(path)
# is equivalent to...
file_object = spe.load()  # and selecting the same file/path
```


##### Automatic imaging and plotting
To quickly view an individual frame, region-of-interest, or spectrum, use the `image()` or `specplot()` methods. For example,
```python
>>> loaded_file.image()  # images the first frame and region of interest
>>> loaded_file.image(f, r)  # images frame 'f' and region of interest 'r'
>>> loaded_file.specplot()  # plots the loaded spectrum
```

##### Accessing metadata
Upon loading, the metadata contained in the file's XML footer is automatically parsed and stored as an `untangle` object in the `footer` variable. Elements and attributes can be accessed by calling the different elements and subelements of footer, ending with the attribute as a string:
```python
>>> sensor_height = loaded_file.footer.SpeFormat.Calibrations.SensorInformation['height']
```
One can print the full element tree by calling the `xmltree()` method.

### Dependencies
  - NumPy - data storage and file reading
  - tkinter - file selection dialog
  - matplotlib - imaging and plotting
  - [untangle](https://github.com/stchris/untangle) - XML parsing

### Version
1.0.0a - initial upload


License
----

MIT

