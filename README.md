# Device Configuration
A repository to keep tracked of the static device information at LCLS. The idea is that
the standard beamline instruments be included here, while those that are often
removed and/or associated with individual experiments are kept elsewhere.

## How to Use
Clone the repository and point a happi Client at the database

```python

import happi
client = happi.Client(path='path/to/device_config/db.json')
```

## Backup
A daily backup is done via CRON job which commits any changes to the `deploy` branch and
pushes to https://github.com/pcdshub/device_config/. This is performed in case an error
is made and the local copy of the `device_config` is lost.
