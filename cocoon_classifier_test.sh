#!/usr/bin/zsh
source activate
conda deactivate
conda activate lacewing
cd /home/jim/Documents/lacewing/transferlearning
python cocoon_classifier_test.py
mv /home/jim/Documents/lacewing/transferlearning/predict/0/* /home/jim/Documents/lacewing/transferlearning/tmp
# cd /home/jim/Documents/lacewing/transferlearning/predict/0
# rm -f *