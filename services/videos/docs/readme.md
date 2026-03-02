# Video service

## Entities

Video
```json
{
  "id": "video_id",
  "name": "video name",
  "year": "video_year",
  "filename": "filename_in_object_sotrage"
}
```

## Database
MongoDB

## API

GET /videos?search=<search>
response
```json
{
  "videos": [
    {
      "id": "video_id",
      "name": "video name",
      "year": "video_year"
    }
  ]
}
```
Returns a list of videos. Searches fields name and year by search field if provided

POST /videos/{id}/prepare
response 200
On request sends a message in video-pipeline.01-ingest. Uses filename as payload and uses hardcoded profiles for now

