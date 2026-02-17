# Video processing flow

## Channels

video-pipeline.01-ingest
video-pipeline.02-transcode
video-pipeline.03-chunking
video-pipeline.04-finalizing

## Services

## Video lifecycle database

Fast tabular database that stores:
- id: PK
- user_id: int
- video_id: str
- source_filename: str
- manifest_filename: str
- config: json
- expires_on: datetime

### Video lifecycle manager

Listens to the channel video-pipeline.01-ingest for the payload:

```json
{
  "input_source": {
    "filename": "file_name_with_path"
  },
  "output_config": {
    "video": {
      "codec": "libx264",
      "width": 1920,
      "height": 1080,
      "fps": 30,
      "bitrate": "5000k",
      "preset": "medium",
      "profile": "high",
      "level": "4.2",
      "pixel_format": "yuv420p",
      "keyframe_interval": 2,
      "b_frames": 2
    },
    "audio": {
      "codec": "aac",
      "bitrate": "192k",
      "sample_rate": 48000,
      "channels": 2
    },
    "container": {
      "format": "mp4",
      "faststart": true
    }
  },
  "chunking": {
    "time_seconds": 3
  },
  "metadata": {
    "user_id": 1,
    "video_id": "id as string"
  }
}
```
On received message the service:
1. Created expires_on as now + 6 hours
2. Saves movie data to the database
3. Posts to channel video-pipeline.02-transcode data input json and adds to metadata video_item_id


Also reads video-pipeline.04-finalizing. Saves manifest in database

CRON: every 10 minutes run cron job and remove folder videos-ready/{video_item_id} for all expired items
Removes associated database entry


### Video encoder

Listens on the channel video-pipeline.02-transcode.
Reads file from the videos-processed/{filename} and encodes it with profile from json.
Saves to videos-ready/{video_item_id} folder
Sends json to video-pipeline.03-chunking with: metadata, chunking and filename only

### Video chunker

Reads video-pipeline.03-chunking and gets json from it.
Reads file from videos-ready/{video_item_id} folder.
Chunks it into pieces from json.chunking.time_seconds max. Saves in
videos-ready/{video_item_id} and creates a manifest file for video player in the end.
Removes big file from videos-ready/{video_item_id} folder

Posts to channel video-pipeline.04-finalizing: manifest_filename and metadata



