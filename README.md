# PointingMemeGenerator

<div align="center">
    <img width="240" src="demo.gif">
  </a>
</div>
Just a small Python utility to make easy memes with perspective image overlays

## **Requirements**

- Python 3.10+
- (Optional) virtualenv / venv

## **Setup**

```pwsh
# Clone the repo
git clone https://github.com/OtarieSupreme/PointingMemeGenerator.git
cd PointingMemeGenerator

# (Optional) Create a virtual environment and activates it
python -m venv .venv # python3 on Linux
.venv\Scripts\Activate

# Install python requirements
pip install -r requirements.txt
```

## **Run**
```pwsh
python main.py # python3 on Linux
```

## **What's next ?** <sub><sup><sub><sup>(If i don't forget abour it)</sup></sub></sup></sub>
- [x] ~~Export to file or clipboard~~
- [ ] Support png as foreground (I forgot)
- [ ] Support drag&drop of urls
- [ ] Save the current setup
- [ ] Easily scroll through the images of a folder



## **Troubleshooting**

- (Windows) If activation fails due to execution policy, run PowerShell as Administrator and allow script execution for the session:

```pwsh
Set-ExecutionPolicy Unrestricted -Scope Process
```
[Source](https://stackoverflow.com/questions/18713086/virtualenv-wont-activate-on-windows)


