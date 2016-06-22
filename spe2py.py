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


def get_files(mult=None):
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

            self.footer = self._read_footer(f)

            (self.roi,
             self.wavelength,
             self.nroi,
             self.nframes,
             self._dtype,
             self.xdim,
             self.ydim) = self._get_specs(f, self.footer)

            (self.xcoord,
             self.ycoord) = self._get_coords(self.roi, self.nroi)

            self.data = self._read_data(f,
                                        self._dtype,
                                        self.nframes,
                                        self.nroi,
                                        self.xcoord,
                                        self.ycoord,
                                        self.xdim,
                                        self.ydim)
        f.close()

    @staticmethod
    def _read_footer(f):
        """
        Loads and parses the source file's xml footer metadata to an 'untangle' object.
        """
        footer_pos = read_at(f, 678, 8, np.uint64)[0]

        f.seek(footer_pos)
        xmlfile = open('xmlFile.tmp', 'w')
        xmltext = f.read()  # .decode('utf-8')

        xmlfile.write(xmltext)

        loaded_footer = untangle.parse('xmlFile.tmp')

        return loaded_footer

    @staticmethod
    def _get_specs(f, footer):
        """
        Returns image and equipment specifications necessary for loading and organizing data
        """
        camerasettings = footer.SpeFormat.DataHistories.DataHistory.Origin.Experiment.Devices.Cameras.Camera
        regionofinterest = camerasettings.ReadoutControl.RegionsOfInterest.CustomRegions.RegionOfInterest

        if isinstance(regionofinterest, list):
            nroi = len(regionofinterest)
            roi = regionofinterest
        else:
            nroi = 1
            roi = np.array([regionofinterest])

        wavelength_string = StringIO(footer.SpeFormat.Calibrations.WavelengthMapping.Wavelength.cdata)
        wavelength = np.loadtxt(wavelength_string, delimiter=',')

        nframes = read_at(f, 1446, 2, np.uint16)[0]
        dtype_code = read_at(f, 108, 2, np.uint16)[0]
        xdim = read_at(f, 42, 2, np.uint16)[0]
        ydim = read_at(f, 656, 2, np.uint16)[0]

        if dtype_code == 0:
            _dtype = np.float32
        elif dtype_code == 1:
            _dtype = np.int32
        elif dtype_code == 2:
            _dtype = np.int16
        elif dtype_code == 3:
            _dtype = np.uint16
        elif dtype_code == 8:
            _dtype = np.uint32

        return roi, wavelength, nroi, nframes, _dtype, xdim, ydim

    @staticmethod
    def _get_coords(roi, nroi):
        """
        Returns x and y pixel coordinates. Used in cases where xdim and ydim do not reflect image dimensions
        (e.g. files containig frames with multiple regions of interest)
        """
        xcoord = [[] for x in range(0, nroi)]
        ycoord = [[] for x in range(0, nroi)]

        for roi_ind in range(0, nroi):
            working_roi = roi[roi_ind]
            ystart = int(working_roi['y'])
            ybinning = int(working_roi['yBinning'])
            yheight = int(working_roi['height'])
            ycoord[roi_ind] = range(ystart, (ystart + yheight), ybinning)

        for roi_ind in range(0, nroi):
            working_roi = roi[roi_ind]
            xstart = int(working_roi['x'])
            xbinning = int(working_roi['xBinning'])
            xwidth = int(working_roi['width'])
            xcoord[roi_ind] = range(xstart, (xstart + xwidth), xbinning)

        return xcoord, ycoord

    @staticmethod
    def _read_data(f, dtype, nframes, nroi, xcoord, ycoord, xdim, ydim):
        """
        Loads raw image data into an nframes X nroi list of arrays.
        """
        f.seek(4100)

        data = [[0 for x in range(nroi)] for y in range(nframes)]
        for frame in range(0, nframes):
            for roi in range(0, nroi):
                if nroi > 1:
                    xdim = len(xcoord[roi])
                    ydim = len(ycoord[roi])
                else:
                    xdim = np.asarray(xdim, np.uint32)
                    ydim = np.asarray(ydim, np.uint32)
                data[frame][roi] = np.fromfile(f, dtype, xdim * ydim).reshape(ydim, xdim)
        return data

    def image(self, frame=0, roi=0):
        """
        Images loaded data for a specific frame and region of interest.
        """
        img = plt.imshow(self.data[frame][roi])
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
        filenames = get_files(True)
    batch = [[] for i in range(0, len(filenames))]
    for file in range(0, len(filenames)):
        batch[file] = SpeFile(filenames[file])
    if len(batch) == 1:
        batch = batch[0]
    print('Successfully loaded %i file(s)' % len(filenames))
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
    for i in range(len(obj)):
        plt.figure()
        obj[i].image()
        plt.show()

