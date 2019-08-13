# mailfetcher

mailfetcher is a Python 3 wrapper against [transferwee](https://github.com/iamleot/transferwee)
to download (and optionally extract) zip archives received via [wetransfer] (https://wetransfer.com). 
Download links for the files being received are extracted from the e-mail messages received upon transfer

## Usage

The entire code is wrapped in a class that is instantiated by passing various options as argument in a dictionary:

```python
from mailfetcher import MailFetcher 
worker = MailFetcher({            
    'server': 'mail.example.com',
    'user': 'john.doe',         
    'pass': 'SuperStr0ngPass', 
    'outdir': '/store/zipfiles/'
})                              
worker.fetch()                 
worker.disconnect()           
```


