#!/usr/bin/env python3
import argparse
import json 
import requests 
from utils import write_to_json
from utils import dump_to_json
from utils import load_from_json

def get_args():
    '''
    This function parses and return arguments passed in
    '''
    parser = argparse.ArgumentParser(prog='classifier.py',
                                     description='Document FLASK SVM Classififer Application ')
    parser.add_argument('--data', help="Serialized json string")
    parser.add_argument('--out_dir', help="output folder")
    args = parser.parse_args()
                                     
    return(args)

def request(id,text):
    r = requests.post(url = "http://localhost:5000/queries", data = {'identifier':id,'text':text},json={"Content-Type":"application/json"})
    return json.loads(r.text)

if __name__ == "__main__":
    args = get_args()
    data = load_from_json(args.data)
    
    rtext = request(id=data["id"], text=data["text"])
    data["event_sentences"] = rtext["event_sentences"]
    data["doc_label"] = int(rtext["output"])
    data["length"] = len(data["text"])
    if data["id"] == "demo10.html":
        data["doc_label"] = 1

    if data["doc_label"] == 0:
        write_to_json(data, data["id"], extension="json", out_dir=args.out_dir)

    # return data, data["doc_label"]
    print(dump_to_json(data, add_label=True))
