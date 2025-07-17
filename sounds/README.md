# Sound Files for Pomodoro Timer

Place your notification sound files in this directory:

- `pomodoro_work.mp3` - Played when switching to work phase
- `pomodoro_break.mp3` - Played when switching to break phase
- `notification.mp3` - Default notification sound (fallback)

## Requirements

- Files must be in MP3 format
- Files should be relatively short (2-5 seconds recommended)
- Make sure FFmpeg is installed on your system for audio playback

## Volume Control

- Use `/pomovolume [0-100]` to adjust notification volume
- Default volume is 50%
- Volume can be adjusted with buttons in the pomodoro control panel
- Test sounds are played when adjusting volume

## Note

If no sound files are found, the bot will still function but won't play audio notifications in voice channels. Text notifications will still work in the study channel.
