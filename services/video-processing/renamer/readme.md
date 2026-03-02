# Renamed service

## Stack
- python
- FastApi
- pytoml

## Availability

This service is meant to be internal and doesn't set any endpoints via API Gateway

## Description

This service receives a name of file and name of video in json format. 
It connects to object storage and takes by name a file from `videos-original` and then
renames it to provided name using the same extension. After that it moves the file to 
`videos-processed`

New file must have a name of type:
`<VIDEO_NAME> (<YEAR>).<HASH>.<EXTENSION>`

File must have a unique hash in name to prevent duplication errors
Files must be saved in single

## Endpoints

POST /
Body:
```json
{
  "file": <FILENAME_WITH_PATH>,
  "name": <VIDEO_NAME>,
  "year": <YEAR>
}
```

Responses:
200 OK
400 if input malformed
500 on server error

