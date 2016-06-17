#!/usr/bin/env python3
"""
spe2py imports a Princeton Instruments LightField (SPE 3.0) file into a python environment.
"""
import numpy as np
import untangle
import tkinter as tk
from tkinter import filedialog as fdialog
from matplotlib import pyplot as plt

# def read_header(filename):
#     f = open(filename, 'rb')
#     header_bytes = f.read(4100)
#     header = np.empty(4100, np.uint8)
#     L = [header_bytes[i:i+1] for i in range(len(header_bytes))]
#     header = np.asarray([int.from_bytes(L[i], byteorder='big') for i in range(len(L))])
#     f.close()
#     return header


class SpeFile(object):

    def __init__(self):
        self.filename = self._get_file()
        with open(self.filename) as f:
            self.footer = self._read_footer(f)
            self.RoI, self.wavelength, self.nRoI, self.nframes, self._dtype, self.xdim, self.ydim = self._get_specs(f, self.footer)
            self.xcoord, self.ycoord = self._get_coords(self.RoI, self.nRoI)
            self.data = self._read_data(f, self._dtype, self.nframes, self.nRoI, self.xcoord, self.ycoord, self.xdim, self.ydim)
        f.close()

        # self.nfile = len(filename) (when mult files are done in future)
        # self.header = header
        # self.footer = parse xml footer
        # self.data = read binary data
        # self.xcoord = assign xcoord from footer
        # self.ycoord = assign ycoord from footer

    @staticmethod
    def _get_file():
        root = tk.Tk()
        root.withdraw()
        filename = fdialog.askopenfilename()
        return filename

    @staticmethod
    def _read_footer(f):
        # f = open(filename, 'rb')
        # f.seek(678)
        # footer_pos = np.fromfile(f, np.uint64, 8)[0]
        # f.seek(footer_pos)
        footer_pos = read_at(f, 678, 8, np.uint64)[0]

        f.seek(footer_pos)
        xmlfile = open('xmlFile.tmp', 'w')
        xmltext = f.read()# .decode('utf-8')

        xmlfile.write(xmltext)

        loaded_footer = untangle.parse('xmlFile.tmp')

        # f.close()
        return loaded_footer

    @staticmethod
    def _get_specs(f, footer):
        camerasettings = footer.SpeFormat.DataHistories.DataHistory.Origin.Experiment.Devices.Cameras.Camera
        regionofinterest = camerasettings.ReadoutControl.RegionsOfInterest.CustomRegions.RegionOfInterest

        if isinstance(regionofinterest, list):
            nRoI = len(regionofinterest)
            RoI = regionofinterest
        else:
            nRoI = 1
            RoI = np.array([regionofinterest])

        wavelength = footer.SpeFormat.Calibrations.WavelengthMapping.Wavelength.cdata

        # nframes = header[1446:1447].astype(np.uint16)[0]
        # dtype_code = header[108:109].astype(np.uint16)[0]

        # f = open(filename, 'rb')
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

        # f.close()
        return RoI, wavelength, nRoI, nframes, _dtype, xdim, ydim

    @staticmethod
    def _get_coords(RoI, nRoI):
        xcoord = [[] for x in range(0, nRoI)]
        ycoord = [[] for x in range(0, nRoI)]

        for roi_ind in range(0, nRoI):
            working_RoI = RoI[roi_ind]
            ystart = int(working_RoI['y'])
            ybinning = int(working_RoI['yBinning'])
            yheight = int(working_RoI['height'])
            ycoord[roi_ind] = range(ystart, (ystart + yheight), ybinning)

        # TODO: figure out wavelength rules
        for roi_ind in range(0, nRoI):
            working_RoI = RoI[roi_ind]
            xstart = int(working_RoI['x'])
            xbinning = int(working_RoI['xBinning'])
            xwidth = int(working_RoI['width'])
            xcoord[roi_ind] = range(xstart, (xstart + xwidth), xbinning)

        return xcoord, ycoord

    @staticmethod
    def _read_data(f, dtype, nframes, nRoI, xcoord, ycoord, xdim, ydim):
        # data = np.empty([nframes, nRoI])
        # f = open(filename, 'rb')
        f.seek(4100)

        # xdim = header[42:43].astype(np.uint16)[0]
        # ydim = header[656:657].astype(np.uint16)[0]

        data = [[0 for x in range(nRoI)] for y in range(nframes)]
        for frame in range(0, nframes):
            for RoI in range(0, nRoI):
                if nRoI > 1:
                    xdim = len(xcoord[RoI])
                    ydim = len(ycoord[RoI])
                else:
                    xdim = np.asarray(xdim, np.uint32)
                    ydim = np.asarray(ydim, np.uint32)
                data[frame][RoI] = np.fromfile(f, dtype, xdim * ydim)
                data[frame][RoI] = data[frame][RoI].reshape(ydim, xdim)
        return data

    def image(self, frame=0, roi=0):
        img = plt.imshow(self.data[frame][roi])
        return img


def print_footer(footer, ind=-1):
    """
    Prints the untangle footer object in tree form to easily view metadata fields. Ignores object elements that contain
    lists (e.g. ..Spectrometer.Turrets.Turret)
    :param footer: xml footer as parsed by untangle
    :param ind: counts tree arrows to print
    :return: printed footer
    """
    if dir(footer):
        ind += 1
        for item in dir(footer):
            if isinstance(getattr(footer, item), list):
                continue
            else:
                print(ind * ' -->', item)
                print_footer(getattr(footer, item), ind)


def read_at(file, pos, size, ntype):
    file.seek(pos)
    return np.fromfile(file, ntype, size)


def imgobject(obj, frame=0, roi=0):
    img = plt.imshow(getattr(obj, 'data')[frame][roi])
    return img


# def _load_size(self):
#     self._xdim = np.int64(self.read_at(42, 1, np.int16)[0])
#     self._ydim = np.int64(self.read_at(656, 1, np.int16)[0])

# def read_at(self, pos, size, ntype):
#     self._fid.seek(pos)
#     return np.fromfile(self._fid, ntype, size)

# def load_img(self):
#     img = self.read_at(4100, self._xdim * self._ydim, np.uint16)
#     return img.reshape((self._ydim, self._xdim))


# def load():
#     file = get_file()
#
#     # loaded_header = read_header(file)
#     loaded_footer = read_footer(file)
#     RoI, wavelength, nRoI, nframes, dtype, xdim, ydim  = get_specs(file, loaded_footer)
#     xcoord, ycoord = get_coords(RoI, nRoI)
#
#     data = read_data(file, dtype, nframes, nRoI, xcoord, ycoord, xdim, ydim)
#
#     # loaded_spe = SPE(file, loaded_header)
#     return data
#     # return loaded_header, loaded_footer, RoI, wavelength, nRoI, nframes, dtype, xcoord, ycoord, data
