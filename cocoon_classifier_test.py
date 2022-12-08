from cocoonclassifier_class import MODEL
import time
# conduct command
# start = time.time()
cocoon = MODEL('cait', 30, 16, 'finetune', "CE", "AdamW")
cocoon.read_model('/home/jim/Documents/lacewing/transferlearning/models/finetune/cait/20221121_233453_bs_16_cait_op_AdamW_ls_CE')
cocoon.read_test_data("./predict", print_name=True)
accuracy, recall, precision, f1_score, result= cocoon.test()
print(f"result:{result}end")
# torch.cuda.empty_cache()
# end = time.time()-start
# print(f'predict time: {end}s')
