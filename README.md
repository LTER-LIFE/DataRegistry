# Title
This web-application is created to help NIOO-KNAW collecting metadata with current and historical primary data.

## Install

Clone project from git
```
mkdir ~/Apps/
cd ~/Apps/
git clone git@gitlab.bioinf.nioo.knaw.nl:nioo-rdm-group/metadata-app.git
git checkout main
```

Install dependencies
```
 #APT
 sudo apt install libcairo2

 # PIPenv python dependencys (requirements.txt)
 pipenv install
```

Systemd
```
sudo cp config/metadata-app.service /etc/systemd/system/
sudo systemctl enable metadata-app.service
systemctl daemon-reload
```

## Usage

```
git clone
```

## Contributing

PRs accepted.

## License