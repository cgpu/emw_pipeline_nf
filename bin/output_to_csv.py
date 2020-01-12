import json
from utils import postprocess
from utils import filename_to_url
from glob import iglob,glob
import argparse
import tqdm
import csv
from coreference_model import coreference_model as cm

def get_args():
    '''
    This function parses and return arguments passed in
    '''
    parser = argparse.ArgumentParser(prog='out_to_csv.py',
                                     description= """This script is written to generate a detailed csv file from json files in a folder.
        The output is sentence based. which contains the following values "url","doc_text","doc_label","doc_is_violent","sentence_number","sentence_text","sentence_label","publish_date","triggers", "places","times","participants","organizers","targets","facilities","trigger_semantic","participant_semantic","organizer_semantic" for each sentences.
        Each of "places","times","participants","organizers","targets","facilities" values represent list of span/ or a span.
       """
       )
    parser.add_argument('--output_type', help="csv or json",default="csv")
    parser.add_argument('--input_folder', help="input folder path",required=True)
    parser.add_argument('--o', help="output file name",default="output_file",required=True)
    parser.add_argument('--date_key', help="output file name",default="publish_date")
    parser.add_argument('--csv_spliter', help="token used as spliter in csv output",default="[SEP]")
    parser.add_argument('--filter_unprotested_sentence', action="store_true",help="filter unprotested sentences",default=False)
    parser.add_argument('--filter_unprotested_doc', action="store_true",help="filter unprotested documents",default=False)
    args = parser.parse_args()

    return(args)

class ToHoldStuff(object):
    def __init__(self):
        self.trigger_list = []
        self.facility_list = []
        self.place_list = []
        self.time_list = []
        self.participant_list = []
        self.target_list = []
        self.organizer_list = []

def add_tag(obj, span, label, tokens):
    text = " ".join([tokens[ind] for ind in span])
    if label == "trigger":
        obj.trigger_list.append(text)
    elif label == "place":
        obj.place_list.append(text)
    elif label == "etime":
        obj.time_list.append(text)
    elif label == "participant":
        obj.participant_list.append(text)
    elif label == "organizer":
        obj.organizer_list.append(text)
    elif label == "target":
        obj.target_list.append(text)
    elif label == "fname":
        obj.facility_list.append(text) 
    else:
        print("Different label : %s" %label)

    return obj


def main():
    list_of_span=[]
    args=get_args()
    files=glob(args.input_folder+"*json")
    if len(files)==0:
        raise RuntimeError("input folder is empty")
    file_log = tqdm.tqdm(total=0, position=1, bar_format='{desc}')
    header_csv=["url","doc_text","doc_label","doc_is_violent","sentence_number","sentence_text","sentence_label","publish_date","triggers", "places","times","participants","organizers","targets","facilities","trigger_semantic","participant_semantic","organizer_semantic"]
    output_file_name=args.o+".csv" if args.output_type=="csv" else args.o+".json"

    with open(output_file_name,"w",errors='surrogatepass',encoding='utf-8') as wr:

        if args.output_type=="csv":
            writer = csv.DictWriter(wr, fieldnames=header_csv)
            writer.writeheader()
            #wr.write(args.csv_spliter.join(header_csv)+"\n") #header
        for filename in tqdm.tqdm(files):
            try:
                    corerefence_sentences=[]
                    output_dicts=[]
                    with open(filename, "r", encoding="utf-8",errors='surrogatepass') as f:
                        data = json.loads(f.read())
                    
                    file_log.set_description_str(f'Current file: {filename}')
                    
                    doc_text_wrote=False
                    if "doc_label" not in data.keys():
                        continue
                    if args.filter_unprotested_doc:
                        if data["doc_label"] == 0:
                            continue 

                    data = postprocess(data)
                    if not data:
                        print("Something wrong with postprocess")
                        continue
        
                    data["id"] = filename_to_url(data["id"])
                    for i, sent_label in enumerate(data["sent_labels"]):
                        if args.filter_unprotested_sentence:
                            if sent_label == 0:
                                continue
                        corerefence_sentences.append({"id":len(output_dicts),"text":data["sentences"][i].replace("\n"," ")})
                        prev_label = "O"
                        curr_span = []
                        obj = ToHoldStuff()
                        tokens = data["tokens"][i]
                        for j,label in enumerate(data["token_labels"][i]):
                            if label == "O" and curr_span:
                                obj = add_tag(obj, curr_span, prev_label, tokens)
                                curr_span = []
        
                            elif label.startswith("B-"):
                                if not curr_span:
                                    curr_span.append(j)
                                else:
                                    obj = add_tag(obj, curr_span, prev_label, tokens)
                                    curr_span = [j]
                                prev_label = label[2:]
        
                            elif label.startswith("I-"):
                                if not curr_span:
                                    curr_span.append(j)
                                else:
                                    if prev_label == label[2:]:
                                        curr_span.append(j)
                                    else:
                                        obj = add_tag(obj, curr_span, prev_label, tokens)
                                        curr_span = [j]
                                prev_label = label[2:]


                        output_dicts.append({"url":data["id"]
                        ,"doc_text":"" if doc_text_wrote else data["text"].replace("\n"," ")
                        ,"publish_date":data[args.date_key].strip("\n")
                        ,"doc_label":str(data["doc_label"])
                        ,"doc_is_violent":str(data["is_violent"])
                        ,"sentence_number":str(i)
                        ,"sentence_text":str(data["sentences"][i]).replace("\n"," ")
                        ,"sentence_label":str(data["sent_labels"][i])
                        ,"triggers":" & ".join(obj.trigger_list)             if len(obj.trigger_list) > 0 else ""
                        ,"places":" & ".join(obj.place_list)                 if len(obj.place_list) > 0 else ""
                        ,"times":" ".join(obj.time_list)                     if len(obj.time_list) > 0 else ""
                        ,"participants":" ".join(obj.participant_list)       if len(obj.participant_list) > 0 else ""
                        ,"organizers":" ".join(obj.organizer_list)           if len(obj.organizer_list) > 0 else ""
                        , "targets":" ".join(obj.target_list)                if len(obj.target_list) > 0 else ""
                        ,"facilities":" ".join(obj.facility_list)            if len(obj.facility_list) > 0 else ""
                        ,"trigger_semantic":data["Trigger_Semantic_label"][i]
                        ,"participant_semantic":data["participant_semantic"][i]
                        ,"organizer_semantic":data["organizer_semantic"][i]})

                        doc_text_wrote=True
                    ###coreference model 
                    
                    #TODO:test the filter mode
                    #if filter was not flagged, default filter is either sentence is positve either contains trigger value
                    if not args.filter_unprotested_sentence or not args.filter_unprotested_doc:
                        assert(len(output_dicts)==len(corerefence_sentences))
                        for i,x in enumerate(output_dicts):
                            if not x["triggers"] or x["sentence_label"]=='1':
                                continue
                            corerefence_sentences[i]=None
                        corerefence_sentences= [x for x in corerefence_sentences if x]
                    #predict all the sentences in corerefence_sentences
                    pred_coref=cm.predict(corerefence_sentences)

                    #extract the groups ids
                    list_of_span=[] 
                    for x in pred_coref: 
                        if len(x)>1: 
                            list_of_span.append([]) 
                            [list_of_span[-1].append(w["id"]) for w in x] 
                    
                    #merge operation 
                    #TODO check if output_dicts[span[i+1]] and output_dicts[span[i]] give the correct answers. 
                    #try it with
                    #temp_i=[dic_i for dic_i,diz in enumerate(t_dict) if diz and diz["id"]==span[0]][0]
                    #temp=t_dict[temp_i]
                    #output_dicts.pop(temp_i)

                    for span in list_of_span: 
                        temp=output_dicts[span[0]]
                        output_dicts[span[0]]=None
                        temp["sentence_number"]=str(span)
                        temp["sentence_label"]=[temp["sentence_label"]]
                        for i in range(len(span)-1):
                            temp2=output_dicts[span[i+1]]
                            output_dicts[span[i+1]]=None
                            temp["sentence_label"].append(temp2['sentence_label'])
                            for x in ["sentence_text","triggers","places","times","participants","organizers","targets","facilities","trigger_semantic","participant_semantic","organizer_semantic"]:
                                # if temp[x] and temp2[x]:
                                #     temp[x]=" [NS] ".join([temp[x],temp2[x]])
                                # elif temp2[x]:
                                #     temp[x]=temp2[x]
                                temp[x]=" [NS] ".join([temp[x],temp2[x]])
                        output_dicts.append(temp)



                    if args.output_type=="csv":
                        [writer.writerow(output_dict) for output_dict in output_dicts if output_dict] #change it to wrtie list 
                    else:
                        [wr.write(json.dumps(output_dict)+"\n") for output_dict in output_dicts if output_dict]#change it to wrtie list 

                    
                
            except Exception as e :

                print(e.with_traceback)
                print(data["id"],"\t",list_of_span,len(output_dicts),len(corerefence_sentences))
                raise RuntimeError

if __name__ == '__main__':
    main()