Below are our web assets. If google cloud run, then assume deployments to qa branch go to qa.domain.net and deployments to prod branch (if exists) or release tags (if prod branch doesn't exist) for release to www.domain.net.  It will take 5 minutes for deploy:



CORE SITES:

1. Physics Github: ~/projects/if -> public Github -> https://github.com/phuctruong/if
2. Phuc.net: ~/projects/phucnet -> gcloud with qa branch/release tag -> https://qa.phuc.net and https://www.phuc.net
3. PZip.net: ~/projects/solaceagi -> gcloud with qa/prod branches -> https://qa.pzip.net and https://www.pzip.net
4. SolaceAGI.com : ~/projects/phucnet -> gcloud with qa branch/release tag -> https://qa.solaceagi.com and https://www.solaceagi.com


Old Brands (just for reference)

5. ~/projects/visioncycle -> gcloud run -> https://qa.visioncycle.com and https://www.visioncycle.net
6. ~/projects/phuclabs -> gcloud run -> https://qa.phuclabs.com and https://www.phuclabs.com




Notes: gcloud should already be installed and setup.  You may need user to login.  Let user know