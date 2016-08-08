#!/usr/bin/env python3
"""
This module imports a Princeton Instruments LightField (SPE 3.0) file into a python environment.
"""
import numpy as np
import untangle
import tkinter as tk
from tkinter import filedialog as fdialog
from io import StringIO
from matplotlib import pyplot as plt


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
    filenames = fdialog.askopenfilenames()
    if not mult:
        filenames = filenames[0]
    root.destroy()
    return filenames


class SpeFile:

    def __init__(self, filename=None):
        if filename:
            self.filename = filename
        else:
            self.filename = get_files()

        with open(self.filename) as f:
            self.header_version = read_at(f, 1992, 3, np.float32)[0]
            assert self.header_version >= 3.0, \
                'This version of spe2py cannot load filetype SPE v. %.1f' % self.header_version

            self.nframes = read_at(f, 1446, 2, np.uint16)[0]
            self.xdim = read_at(f, 42, 2, np.uint16)[0]
            self.ydim = read_at(f, 656, 2, np.uint16)[0]

            self.footer = self._read_footer(f)
            self.dtype = self._get_dtype(f)

            # Note: these methods depend on self.footer
            self.roi, self.nroi = self._get_roi_info()
            self.wavelength = self._get_wavelength()

            self.xcoord, self.ycoord = self._get_coords()

            self.data = self._read_data(f)
        f.close()

    @staticmethod
    def _read_footer(f):
        """
        Loads and parses the source file's xml footer metadata to an 'untangle' object.
        """
        footer_pos = read_at(f, 678, 8, np.uint64)[0]

        f.seek(footer_pos)
        xmlfile = open('xmlFile.tmp', 'w')
        xmltext = f.read()

        xmlfile.write(xmltext)

        loaded_footer = untangle.parse('xmlFile.tmp')

        return loaded_footer

    @staticmethod
    def _get_dtype(f):
        dtype_code = read_at(f, 108, 2, np.uint16)[0]

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

    def _get_roi_info(self):
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
            roi = np.array([regionofinterest])

        return roi, nroi

    def _get_wavelength(self):
        try:
            wavelength_string = StringIO(self.footer.SpeFormat.Calibrations.WavelengthMapping.Wavelength.cdata)
        except AttributeError:
            print("XML Footer was not loaded prior to calling _get_roi_info")
            raise

        wavelength = np.loadtxt(wavelength_string, delimiter=',')

        return wavelength

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

    def _read_data(self, f):
        """
        Loads raw image data into an nframes X nroi list of arrays.
        """
        f.seek(4100)

        data = [[0 for _ in range(self.nroi)] for _ in range(self.nframes)]
        for frame in range(0, self.nframes):
            for region in range(0, self.nroi):
                if self.nroi > 1:
                    data_xdim = len(self.xcoord[region])
                    data_ydim = len(self.ycoord[region])
                else:
                    data_xdim = np.asarray(self.xdim, np.uint32)
                    data_ydim = np.asarray(self.ydim, np.uint32)
                data[frame][region] = np.fromfile(f, self.dtype, data_xdim * data_ydim).reshape(data_ydim, data_xdim)
        return data

    def image(self, frame=0, roi=0):
        """
        Images loaded data for a specific frame and region of interest.
        """
        img = plt.imshow(self.data[frame][roi])
        plt.title(self.filename)
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


def load(filenames=None):
    """Allows user to load multiple files at once. Each file is stored as an SpeFile object in the list batch."""
    if filenames is None:
        filenames = get_files(mult=True)
    batch = [[] for _ in range(0, len(filenames))]
    for file in range(0, len(filenames)):
        batch[file] = SpeFile(filenames[file])
    return_type = "list of SpeFile objects"
    if len(batch) == 1:
        batch = batch[0]
        return_type = "SpeFile object"
    print('Successfully loaded %i file(s) in a %s' % (len(filenames), return_type))
    return batch


def read_at(file, pos, size, ntype):
    """
    Reads SPE source file at specific byte position.
    Adapted from https://scipy.github.io/old-wiki/pages/Cookbook/Reading_SPE_files.html
    """
    file.seek(pos)
    return np.fromfile(file, ntype, size)


def imgobject(speobject, frame=0, roi=0):
    """Unbound function for imaging loaded data"""
    img = plt.imshow(getattr(speobject, 'data')[frame][roi])
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
