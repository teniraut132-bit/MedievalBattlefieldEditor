# Medieval Battlefield Editor

## Automatic updates

The launcher checks GitHub Releases for the newest stable version.

Repository: teniraut132-bit/MedievalBattlefieldEditor

Release asset: MedievalBattlefieldEditor-Windows-x64.zip

A SHA-256 companion file is published for integrity verification.

## Release process

1. Commit changes to main.
2. Create a semantic version tag such as v5.0.0.
3. GitHub Actions builds the Windows editor and launcher.
4. A GitHub Release is created with the ZIP and SHA-256 file.
5. Installed launchers detect the new stable release and update the editor.

Never commit passwords or access tokens.
