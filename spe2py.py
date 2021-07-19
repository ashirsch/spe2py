#!/usr/bin/env python3
"""
This module imports a Princeton Instruments LightField (SPE 3.0) file into a python environment.
"""
import numpy as np
import untangle
import tkinter as tk
from tkinter import filedialog as fdialog
from io import StringIO
#import matplotlib
#matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib import cm


def get_files(mult=False):
    """
    Uses tkinter to allow UI source file selection
    Adapted from: http://stackoverflow.com/a/7090747
    """
    root = tk.Tk()
    root.withdraw()
    root.overrideredirect(True)
    root.geometry('0x0+0+0')
    root.deiconify()
    root.lift()
    root.focus_force()
    filepaths = fdialog.askopenfilenames()
    if not mult:
        filepaths = filepaths[0]
    root.destroy()
    return filepaths


class SpeFile:
    def __init__(self, filepath=None):
        if filepath is not None:
            assert isinstance(filepath, str), 'Filepath must be a single string'
            self.filepath = filepath
        else:
            self.filepath = get_files()

        with open(self.filepath) as file:
            self.header_version = read_at(file, 1992, 3, np.float32)[0]
            assert self.header_version >= 3.0, \
                'This version of spe2py cannot load filetype SPE v. %.1f' % self.header_version

            self.nframes = read_at(file, 1446, 2, np.uint16)[0]

            self.footer = self._read_footer(file)
            self.dtype = self._get_dtype(file)

            # Note: these methods depend on self.footer
            self.xdim, self.ydim = self._get_dims()
            self.roi, self.nroi = self._get_roi_info()
            self.wavelength = self._get_wavelength()

            self.xcoord, self.ycoord = self._get_coords()

            self.data, self.metadata, self.metanames = self._read_data(file)
        file.close()

    @staticmethod
    def _read_footer(file):
        """
        Loads and parses the source file's xml footer metadata to an 'untangle' object.
        """
        footer_pos = read_at(file, 678, 8, np.uint64)[0]

        file.seek(footer_pos)
        xmltext = file.read()

        parser = untangle.make_parser()
        sax_handler = untangle.Handler()
        parser.setContentHandler(sax_handler)

        parser.parse(StringIO(xmltext))

        loaded_footer = sax_handler.root

        return loaded_footer

    @staticmethod
    def _get_dtype(file):
        """
        Returns the numpy data type used to encode the image data by reading the numerical code in the binary header.
        Reference: Princeton Instruments File Specification pdf
        """
        dtype_code = read_at(file, 108, 2, np.uint16)[0]

        if dtype_code == 0:
            dtype = np.float32
        elif dtype_code == 1:
            dtype = np.int32
        elif dtype_code == 2:
            dtype = np.int16
        elif dtype_code == 3:
            dtype = np.uint16
        elif dtype_code == 8:
            dtype = np.uint32
        else:
            raise ValueError("Unrecognized data type code: %.2f. Value should be one of {0, 1, 2, 3, 8}" % dtype_code)

        return dtype

    def _get_meta_dtype(self):
        meta_types = []
        meta_names = []
        prev_item = None
        for item in dir(self.footer.SpeFormat.MetaFormat.MetaBlock):
            if item == 'TimeStamp' and prev_item != 'TimeStamp':  # Specify ExposureStarted vs. ExposureEnded
                for element in self.footer.SpeFormat.MetaFormat.MetaBlock.TimeStamp:
                    meta_names.append(element['event'])
                    meta_types.append(element['type'])
                prev_item = 'TimeStamp'
            elif item == 'GateTracking' and prev_item != 'GateTracking':  # Specify Delay vs. Width
                for element in self.footer.SpeFormat.MetaFormat.MetaBlock.GateTracking:
                    meta_names.append(element['component'])
                    meta_types.append(element['type'])
                prev_item = 'GateTracking'
            elif prev_item != item:  # All other metablock names only have one possible value
                meta_names.append(item)
                meta_types.append(getattr(self.footer.SpeFormat.MetaFormat.MetaBlock, item)['type'])
                prev_item = item

        for index, type_str in enumerate(meta_types):
            if type_str == 'Int64':
                meta_types[index] = np.int64
            else:
                meta_types[index] = np.float64

        return meta_types, meta_names

    def _get_roi_info(self):
        """
        Returns region of interest attributes and numbers of regions of interest
        """
        try:
            camerasettings = self.footer.SpeFormat.DataHistories.DataHistory.Origin.Experiment.Devices.Cameras.Camera
            regionofinterest = camerasettings.ReadoutControl.RegionsOfInterest.CustomRegions.RegionOfInterest
        except AttributeError:
            print("XML Footer was not loaded prior to calling _get_roi_info")
            raise

        if isinstance(regionofinterest, list):
            nroi = len(regionofinterest)
            roi = regionofinterest
        else:
            nroi = 1
            roi = [regionofinterest]

        return roi, nroi

    def _get_wavelength(self):
        """
        Returns wavelength-to-pixel map as stored in XML footer
        """
        try:
            wavelength_string = StringIO(self.footer.SpeFormat.Calibrations.WavelengthMapping.Wavelength.cdata)
        except AttributeError:
            """
            possibly because a calibration is present.
            Try getting the WavelengthError.cdata instead of Wavelength.cdata when calibration is present.
            """
            try:
                wavelengthErrorStr = self.footer.SpeFormat.Calibrations.WavelengthMapping.WavelengthError.cdata
                wavelengthErrorStrStream = StringIO(wavelengthErrorStr.replace(" ", "\n"))
                wavelengthError = np.loadtxt(wavelengthErrorStrStream, delimiter=',')
                return wavelengthError[:,0]
            except:
                print("XML Footer was not loaded prior to calling _get_wavelength")
                return
        except IndexError:
            print("XML Footer does not contain Wavelength Mapping information")
            return





        wavelength = np.loadtxt(wavelength_string, delimiter=',')

        return wavelength

    def _get_dims(self):
        """
        Returns the x and y dimensions for each region as stored in the XML footer
        """
        xdim = [int(block["width"]) for block in self.footer.SpeFormat.DataFormat.DataBlock.DataBlock]
        ydim = [int(block["height"]) for block in self.footer.SpeFormat.DataFormat.DataBlock.DataBlock]

        return xdim, ydim

    def _get_coords(self):
        """
        Returns x and y pixel coordinates. Used in cases where xdim and ydim do not reflect image dimensions
        (e.g. files containing frames with multiple regions of interest)
        """
        xcoord = [[] for _ in range(0, self.nroi)]
        ycoord = [[] for _ in range(0, self.nroi)]

        for roi_ind in range(0, self.nroi):
            working_roi = self.roi[roi_ind]
            ystart = int(working_roi['y'])
            ybinning = int(working_roi['yBinning'])
            yheight = int(working_roi['height'])
            ycoord[roi_ind] = range(ystart, (ystart + yheight), ybinning)

        for roi_ind in range(0, self.nroi):
            working_roi = self.roi[roi_ind]
            xstart = int(working_roi['x'])
            xbinning = int(working_roi['xBinning'])
            xwidth = int(working_roi['width'])
            xcoord[roi_ind] = range(xstart, (xstart + xwidth), xbinning)

        return xcoord, ycoord

    def _read_data(self, file):
        """
        Loads raw image data into an nframes X nroi list of arrays.
        """
        file.seek(4100)

        frame_stride = int(self.footer.SpeFormat.DataFormat.DataBlock['stride'])
        frame_size = int(self.footer.SpeFormat.DataFormat.DataBlock['size'])
        metadata_size = frame_stride - frame_size
        if metadata_size != 0:
            metadata_dtypes, metadata_names = self._get_meta_dtype()
            metadata = np.zeros((self.nframes, len(metadata_dtypes)))
        else:
            metadata_dtypes, metadata_names = None, None
            metadata = None

        data = [[0 for _ in range(self.nroi)] for _ in range(self.nframes)]
        for frame in range(0, self.nframes):
            for region in range(0, self.nroi):
                if self.nroi > 1:
                    data_xdim = len(self.xcoord[region])
                    data_ydim = len(self.ycoord[region])
                else:
                    data_xdim = np.asarray(self.xdim[region], np.uint32)
                    data_ydim = np.asarray(self.ydim[region], np.uint32)
                data[frame][region] = np.fromfile(file, self.dtype, data_xdim * data_ydim).reshape(data_ydim, data_xdim)
            if metadata_dtypes is not None:
                for meta_block in range(len(metadata_dtypes)):
                    metadata[frame, meta_block] = np.fromfile(file, dtype=metadata_dtypes[meta_block], count=1)

        return data, metadata, metadata_names

    def image(self, frame=0, roi=0):
        """
        Images loaded data for a specific frame and region of interest.
        """
        img = plt.imshow(self.data[frame][roi], cmap=cm.get_cmap('hot'))
        plt.title(self.filepath)
        return img

    def specplot(self, frame=0, roi=0):
        """
        Plots loaded data for a specific frame, assuming the data is a one dimensional spectrum.
        """
        spectrum = plt.plot(self.wavelength.transpose(), self.data[frame][roi].transpose())
        plt.grid()
        return spectrum

    def xmltree(self, footer, ind=-1):
        """
        Prints the untangle footer object in tree form to easily view metadata fields. Ignores object elements that
        contain lists (e.g. ..Spectrometer.Turrets.Turret).
        """
        if dir(footer):
            ind += 1
            for item in dir(footer):
                if isinstance(getattr(footer, item), list):
                    continue
                else:
                    print(ind * ' -->', item)
                    self.xmltree(getattr(footer, item), ind)


def load(filepaths=None):
    """
    Allows user to load multiple files at once. Each file is stored as an SpeFile object in the list batch.
    """
    if filepaths is None:
        filepaths = get_files(mult=True)
    elif isinstance(filepaths, str):
        filepaths = [filepaths]
    batch = [[] for _ in range(0, len(filepaths))]
    for file in range(0, len(filepaths)):
        batch[file] = SpeFile(filepaths[file])
    return_type = "list of SpeFile objects"
    if len(batch) == 1:
        batch = batch[0]
        return_type = "SpeFile object"
    print('Successfully loaded %i file(s) in a %s' % (len(filepaths), return_type))
    return batch


def read_at(file, pos, size, ntype):
    """
    Reads SPE source file at specific byte position.
    Adapted from https://scipy.github.io/old-wiki/pages/Cookbook/Reading_SPE_files.html
    """
    file.seek(pos)
    return np.fromfile(file, ntype, size)


def imgobject(speobject, frame=0, roi=0):
    """
    Unbound function for imaging loaded data
    """
    img = plt.imshow(getattr(speobject, 'data')[frame][roi], cmap=cm.get_cmap('hot'))
    return img


if __name__ == "__main__":
    obj = load()
    if isinstance(obj, list):
        for i in range(len(obj)):
            plt.figure()
            obj[i].image()
    else:
        plt.figure()
        obj.image()
    plt.show()
