from __future__ import division

import array
import asyncio
from base64 import b64encode
from io import BytesIO
from threading import Lock
import traceback
import time

from audio_common_msgs.msg import AudioData
from hume import HumeStreamClient
from hume.models.config import BurstConfig
from hume.models.config import ProsodyConfig
from hume import StreamSocket
import numpy as np
from pydub import AudioSegment
import rospy
import soundfile as sf

from audio_buffer import AudioBuffer


class AudioBuffer(object):

    def __init__(self, topic_name='~audio',
                 input_sample_rate=16000,
                 window_size=10.0,
                 bitdepth=16,
                 n_channel=1, target_channel=0,
                 get_latest_data=False,
                 discard_data=False,
                 auto_start=False):
        self.is_subscribing = True
        self.get_latest_data = get_latest_data
        self.discard_data = discard_data
        self._window_size = window_size
        self.audio_buffer_len = int(self._window_size * input_sample_rate)
        self.lock = Lock()
        self.bitdepth = bitdepth
        self.n_channel = n_channel
        self.target_channel = min(self.n_channel - 1, max(0, target_channel))
        self.input_sample_rate = input_sample_rate
        self.type_code = {}
        for code in ['b', 'h', 'i', 'l']:
            self.type_code[array.array(code).itemsize] = code

        self.dtype = self.type_code[self.bitdepth / 8]
        self.audio_buffer = np.array([], dtype=self.dtype)

        self.max_value = 2 ** (self.bitdepth - 1) - 1

        self.topic_name = topic_name

        if auto_start:
            self.subscribe()

    def __len__(self):
        return len(self.audio_buffer)

    @property
    def window_size(self):
        return self._window_size

    @window_size.setter
    def window_size(self, size):
        with self.lock:
            self._window_size = size
            self.audio_buffer_len = int(self._window_size
                                        * self.input_sample_rate)
            self.audio_buffer = np.array([], dtype=self.dtype)

    @staticmethod
    def from_rosparam(**kwargs):
        n_channel = rospy.get_param('~n_channel', 1)
        target_channel = rospy.get_param('~target_channel', 0)
        mic_sampling_rate = rospy.get_param('~mic_sampling_rate', 16000)
        bitdepth = rospy.get_param('~bitdepth', 16)
        return AudioBuffer(input_sample_rate=mic_sampling_rate,
                           bitdepth=bitdepth,
                           n_channel=n_channel,
                           target_channel=target_channel,
                           **kwargs)

    def subscribe(self):
        self.audio_buffer = np.array([], dtype=self.dtype)
        self.sub_audio = rospy.Subscriber(
            self.topic_name, AudioData, self.audio_cb)

    def unsubscribe(self):
        self.sub_audio.unregister()

    def _read(self, size, normalize=False):
        with self.lock:
            if self.get_latest_data:
                audio_buffer = self.audio_buffer[-size:]
            else:
                audio_buffer = self.audio_buffer[:size]
                if self.discard_data:
                    self.audio_buffer = self.audio_buffer[size:]
        if normalize is True:
            audio_buffer = audio_buffer / self.max_value
        return audio_buffer

    def sufficient_data(self, size):
        return len(self.audio_buffer) < size

    def read(self, size=None, wait=False, normalize=False):
        if size is None:
            size = self.audio_buffer_len
        size = int(size * self.input_sample_rate)
        while wait is True \
                and not rospy.is_shutdown() and len(self.audio_buffer) < size:
            rospy.sleep(0.001)
        return self._read(size, normalize=normalize)

    def close(self):
        try:
            self.sub_audio.unregister()
        except Exception:
            pass
        self.audio_buffer = np.array([], dtype=self.dtype)

    def audio_cb(self, msg):
        audio_buffer = np.frombuffer(msg.data, dtype=self.dtype)
        audio_buffer = audio_buffer[self.target_channel::self.n_channel]
        with self.lock:
            self.audio_buffer = np.append(
                self.audio_buffer, audio_buffer)
            self.audio_buffer = self.audio_buffer[
                -self.audio_buffer_len:]


rospy.init_node('hume_sound')


audio_buffer = AudioBuffer(topic_name='/audio/audio',
                           window_size=2,
                           auto_start=True)
api_key = 'VJnmO6ztAR1dpqSkoAQuzPMBETpwPams6PnezH20Xddo2A0y'


def on_shutdown():
    print('on_shutdown called')
    audio_buffer.unsubscribe()
    audio_buffer.audio_buffer = np.array([], dtype=audio_buffer.dtype)

rospy.on_shutdown(on_shutdown)

rospy.sleep(1.0)



def encode_audio():
    wav_outpath = '/tmp/hoge.wav'
    bytes_io = BytesIO()
    with sf.SoundFile(wav_outpath, mode='w',
                      samplerate=audio_buffer.input_sample_rate,
                      channels=audio_buffer.n_channel,
                      format='wav') as f:
        tmp = audio_buffer.read()
        f.write(tmp)

    segment = AudioSegment.from_file(file=wav_outpath,
                                     format="wav")
    segment.export(bytes_io, format="wav")
    return b64encode(bytes_io.read())


client = HumeStreamClient(api_key)
configs = [BurstConfig(),ProsodyConfig()]


async def send_audio():
    try:
        async with client.connect(configs) as socket:
            socket: StreamSocket

            while True:
                result = None
                await socket.reset_stream()
                send_bytes = encode_audio()
                print(len(send_bytes))
                if len(send_bytes) <= 100:
                    break
                result = await socket.send_bytes(send_bytes)
                time.sleep(1.0)
                print(result)
    except Exception:
        print(traceback.format_exc())


asyncio.run(send_audio())
