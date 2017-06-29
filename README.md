# JINS Virtual Fit Retriever

Python3.6以上

## Prepare1
Set .envrc for direnv
```
 $ cd <this project root>
 $ direnv edit .
 
export YNU_AUTH_ID=XXXXXX
export YNU_AUTH_PASS=XXXX
export AWS_ACCESS_KEY_ID=<YOUR_AWS_ACCESS_KEY>
export AWS_SECRET_ACCESS_KEY=<YOUR_AWS_SECRET_KEY>
export AWS_DEFAULT_REGION=ap-northeast-1
export TF_VAR_access_key=<YOUR_AWS_ACCESS_KEY>
export TF_VAR_secret_key=<YOUR_AWS_SECRET_KEY>
export TF_VAR_region=ap-northeast-1
```

## Prepare2
Set cron  
参照: [https://superuser.com/questions/359580/error-adding-cronjobs-in-mac-os-x-lion](https://superuser.com/questions/359580/error-adding-cronjobs-in-mac-os-x-lion)
```
$ crontab -e
0 */3 * * * /Users/uejun/sandbox/try_selenium/auto_network_auth.sh
```
最初は下記のようなエラーになる
```
crontab: no crontab for uejun - using an empty one
crontab: temp file must be edited in place
```
なので 
1) Add to .zshrc
```
alias crontab="VIM_CRONTAB=true crontab"
```
2) Add to .vimrc
```
if $VIM_CRONTAB == "true"
    set nobackup
    set nowritebackup
endif
```
3) 
``` 
$ source ~/.zshrc
```
4) 再度編集
```
$ crontab -e

crontab: installing new crontab
と返ればOK.
```
5) 確認
```
$ crontab -l
$ cat /var/email/uejun
```

## Prepare3
```
$ brew install chromedriver
```

## Prepare4
```angular2html
$ pip install -r requirements.txt
```

## Execute0
```angular2html
$ cd infla/terraform
$ terraform plan
$ terraform apply # if needed
```
## Execute
```angular2html
$ python jins.py
```

