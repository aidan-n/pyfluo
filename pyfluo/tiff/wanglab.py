from pyfluo.pf_base import pfBase
from tifffile import TiffFile
import numpy as np
from pyfluo.movies import Movie, LineScan
from pyfluo.util import *
import time as pytime

CHANNEL_IMG = 0
CHANNEL_STIM = 1


class MultiChannelTiff(pfBase):
    """An object that holds multiple movie-like (from movies module) objects as channels.
    
    This class is currently exclusively for creation from WangLabScanImageTiff's. Its main goal is to circumvent the need to load a multi-channel tiff file more than once in order to attain movies from its multiple channels.
    
    **Attributes:**
        * **movies** (*list*): list of Movie objects.
        
        * **name** (*str*): a unique name generated for the object when instantiated
        
    """
    def __init__(self, raw, klass=Movie, **kwargs):
        """Initialize a MultiChannelTiff object.
        
        **Parameters:**
            * **raw** (*str* / *WangLabScanImageTiff* / *list* thereof): list of movies.
            * **skip** (*list*): a two-item list specifying how many frames to skip from the start (first item) and end (second item) of each movie.
            * **klass** (*class*): the type of class in which the movies should be stored (currently supports pyfluo.Movie or pyfluo.LineScan)
        """
        super(MultiChannelTiff, self).__init__() 
        
        self.channels = []
        
        if type(raw) != list:
            raw = [raw]
        widgets=[' Loading tiffs:', Percentage(), Bar()]
        pbar = ProgressBar(widgets=widgets, maxval=len(raw)).start()
        for idx,item in enumerate(raw):
            if type(item) == str:
                raw[idx] = WangLabScanImageTiff(item)
                pbar.update(idx+1)
            elif type(item) != WangLabScanImageTiff:
                raise Exception('Invalid input for movie. Should be WangLabScanImageTiff or tiff filename.')
        tiffs = raw
        pbar.finish()
        
        self.n_tiffs = len(tiffs)
        n_channels = tiffs[0].n_channels
        if not all([i.n_channels==n_channels for i in tiffs]):
            raise Exception('Channel number inconsistent among provided tiffs.')
        
        for ch in xrange(n_channels):    
            movie = None
            for item in tiffs:              
                chan = item[ch]
                mov = klass(data=chan['data'], info=chan['info'], **kwargs)
                
                if movie == None:   movie = mov
                else:   movie.append(mov)
            self.channels.append(movie)
            
    def get_channel(self, i):
        """Retrieve the movie corresponding to a specified channel.

        .. note:: Note that this method is equivalent to the use of indexing. For example: ``mct.get_channel(1)`` is equivalent to ``mct[1]``.

        **Parameters:**
            * **i** (*int*): index of channel to return.

        **Returns:**
            Object of type *klass*, described in constructor, corresponding to channel ``i``.
        """
        return self.channels[i]
    def __getitem__(self, i):
        return self.get_channel(i)
    def __len__(self):
        return len(self.channels)
    def __str__(self):
        return '\n'.join([
        'MultiChannelTiff object.',
        "Contains %i channels."%len(self),
        "Acquired from %i tiff files."%self.n_tiffs,
        ])
class WangLabScanImageTiff(object):

    def __init__(self, filename):
        tiff_file = TiffFile(filename)
        first_pg = tiff_file[0].asarray()
        data = np.empty((len(tiff_file), np.shape(first_pg)[0], np.shape(first_pg)[1]))
        for pidx,page in enumerate(tiff_file):
            data[pidx,:,:] = page.asarray()
        
        inf = self.parse_page_info(tiff_file[0].image_description) 
        page_info = [inf for i in xrange(len(tiff_file))]
    
        ex_info = page_info[0]
        self.n_channels = int(ex_info['state.acq.numberOfChannelsAcquire'])
        self.channels = self.split_channels(data, page_info)
        self.source_name = filename
    def split_channels(self, data, page_info):
        if len(data)%float(self.n_channels):
            raise('Tiff pages do not correspond properly to number of channels. Check tiff parsing.')
        
        channels = []
        for ch in xrange(self.n_channels):
            channel = {}
            channel['data'] = np.concatenate([[i] for i in data[ch::self.n_channels]])
            channel['info'] = page_info[ch::self.n_channels]
            channels.append(channel)
        return channels
        
    def parse_page_info(self, img_description):
        desc = ''.join([ch for ch in img_description if ord(ch)<127])
        fields = [field.split('=') for field in desc.split('\n') if len(field.split('='))>1]
        info = {}
        for field in fields:
            info[field[0]] = field[1]
        return info
    def __getitem__(self, idx):
        return self.channels[idx]
if __name__ == "__main__":
    testtif = '/Users/Benson/Desktop/5_24_2013_GR_100ms_5p_071.tif'
    tdata = WangLabScanImageTiff(testtif)

"""
http://stackoverflow.com/questions/6686550/how-to-animate-a-time-ordered-sequence-of-matplotlib-plots

Old method of processing tiffs:

from PIL import Image

tiff_file = Image.open(filename)
img_size = [raw_tiff_file.size[1], raw_tiff_file.size[0]]
self.data = []
try:
    while 1:
        raw_tiff_file.seek(raw_tiff_file.tell()+1)
        self.data.append( np.reshape(raw_tiff_file.getdata(),img_size) )
except EOFError:
    pass
self.data = np.dstack(self.data)
"""
