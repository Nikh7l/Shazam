import sounddevice as sd
import soundfile as sf
import click
import numpy as np

# Default values
DEFAULT_SAMPLE_RATE = 44100  # Standard sample rate
DEFAULT_CHANNELS = 1         # Mono audio

@click.command()
@click.option('--duration', '-d', default=7, help='Duration of the recording in seconds.', type=int)
@click.option('--output', '-o', default='recorded_clip.wav', help='Output filename for the recording.', type=click.Path())
@click.option('--samplerate', '-sr', default=DEFAULT_SAMPLE_RATE, help='Recording sample rate in Hz.', type=int)
@click.option('--channels', '-c', default=DEFAULT_CHANNELS, help='Number of recording channels (1 for mono, 2 for stereo).', type=int)
@click.option('--list-devices', '-l', is_flag=True, help='List available audio devices and exit.')
@click.option('--device', '-dev', help='Input device ID (integer) or name substring. See --list-devices.', default=None)
def record_audio(duration, output, samplerate, channels, list_devices, device):
    """Records audio from the microphone for a specified duration and saves it to a file."""
    if list_devices:
        click.echo("Available audio input devices:")
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            # Check if it's an input device by looking for input channels
            if dev['max_input_channels'] > 0:
                click.echo(f"  ID: {i}, Name: {dev['name']}, Channels: {dev['max_input_channels']} (Input)")
        return

    actual_device = device
    if device is not None:
        try:
            actual_device = int(device)
            click.echo(f"Using device ID: {actual_device}")
        except ValueError:
            click.echo(f"Searching for device containing name: '{device}'")
            # No direct search by name in sounddevice query_devices, user needs to pick ID
            # Or, one could iterate and find a match, but for CLI, ID is more robust.
            # For simplicity, we'll rely on the user providing the correct ID if not default.
            pass # actual_device remains the string name or None

    click.echo(f"Preparing to record {duration} seconds of audio...")
    click.echo(f"Sample rate: {samplerate} Hz, Channels: {channels}")
    click.echo(f"Output file: {output}")
    if actual_device is not None:
        click.echo(f"Using device: {actual_device}")
    else:
        click.echo("Using default input device.")

    click.echo("Starting recording in 3 seconds...")
    sd.sleep(1000) # 1 sec
    click.echo("2...")
    sd.sleep(1000) # 1 sec
    click.echo("1...")
    sd.sleep(1000) # 1 sec
    click.echo("RECORDING... Speak or play audio now!")

    try:
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='float32', device=actual_device)
        sd.wait()  # Wait until recording is finished
        click.echo("Recording finished.")

        # Save as WAV file
        sf.write(output, recording, samplerate)
        click.echo(click.style(f"✅ Audio successfully recorded and saved to {output}", fg='green'))
    except Exception as e:
        click.echo(click.style(f"❌ Error during recording or saving: {e}", fg='red'))
        click.echo("If you specified a device, ensure it's correct. Try 'python record_audio.py --list-devices'.")

if __name__ == '__main__':
    record_audio()
