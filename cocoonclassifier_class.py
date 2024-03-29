# -*- coding: utf-8 -*-
"""cocoonclassifier-class

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1I2u3K6yaNbV6HCBVw321N2mhPjQ2Uf3I
"""

from importlib.metadata import requires
import torch
import torchvision
from torchvision import datasets,transforms, models
from torchvision.utils import make_grid
import os
import numpy as np
import matplotlib.pyplot as plt
from torch.autograd import Variable 
import time
import pickle
from torchsummary import summary

torch.set_default_tensor_type('torch.cuda.FloatTensor')

class MODEL():
    def __init__(self, modelname, n_epochs, batch_size, train_mode, loss, optimizer):
        self.train_mode = train_mode
        self.modelname = modelname
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        self.train_mode = train_mode
        self.loss = loss
        self.optimizer_str = optimizer
        if self.modelname == "vgg16":
            self.model = models.vgg16(pretrained=True)
            if self.train_mode == "feature_extraction" :
                for param in self.model.parameters():
                    param.requires_grad = False
            # for param in self.model.parameters():
            #     print(param.requires_grad)

            self.model.classifier = torch.nn.Sequential(torch.nn.Linear(25088, 4096),
                                                torch.nn.ReLU(),
                                                torch.nn.Dropout(p=0.5),
                                                torch.nn.Linear(4096, 4096),
                                                torch.nn.ReLU(),
                                                torch.nn.Dropout(p=0.5),
                                                torch.nn.Linear(4096, 2))
            # print(self.model)
        elif self.modelname == "resnet":
            self.model = models.resnet50(pretrained=True)
            if self.train_mode == "feature_extraction" :
                for param in self.model.parameters():
                    param.requires_grad = False
            
            self.model.fc = torch.nn.Sequential(
               torch.nn.Linear(2048, 128),
               torch.nn.ReLU(),
               torch.nn.Dropout(p=0.5),
               torch.nn.Linear(128, 2))

        elif self.modelname == "googlenet":
            self.model = models.googlenet(pretrained=True)
            if self.train_mode == "feature_extraction":
                for param in self.model.parameters():
                    param.requires_grad = False
            self.model.fc = torch.nn.Sequential(
               torch.nn.Linear(1024, 128),
               torch.nn.ReLU(),
               torch.nn.Dropout(p=0.5),
               torch.nn.Linear(128, 2),
               )
        elif  self.modelname == "cait":
            self.model = torch.hub.load("facebookresearch/deit", "cait_XXS24_224",pretrained=True)
            # if self.train_mode == "feature_extraction":
            for param in self.model.parameters():
                param.requires_grad = False
            if self.loss == "CE":
                self.model.head = torch.nn.Sequential(torch.nn.Linear(192, 80),
                                                    torch.nn.ReLU(),
                                                    torch.nn.Dropout(p=0.5),
                                                    torch.nn.Linear(80, 2))
            else:
                self.model.head = torch.nn.Sequential(torch.nn.Linear(192, 80),
                                                    torch.nn.ReLU(),
                                                    torch.nn.Dropout(p=0.5),
                                                    torch.nn.Linear(80, 1))                
            # self.model.head = torch.nn.Sequential(torch.nn.Linear(192, 80, bias=True),
            #                                     torch.nn.ReLU(),
            #                                     torch.nn.Dropout(p=0.5),
            #                                     torch.nn.Linear(80, 1))
    


        self.model = self.model.cuda()
        # out = self.model(torch.randn( 4, 224, 224))
        # print(out.shape)
        # summary(self.model, (3,224,224))
        # print(self.model)
        # print(self.model)
        if self.loss == "BCE":
            self.cost = torch.nn.BCEWithLogitsLoss()
        elif self.loss == "CE":
            self.cost = torch.nn.CrossEntropyLoss() 
        elif self.loss == "SM":
            self.cost = torch.nn.SoftMarginLoss()
        # self.optimizer = torch.optim.AdamW(self.model.parameters(), capturable=True) 
        if self.optimizer_str == "SGD":
            self.optimizer = torch.optim.SGD(self.model.parameters(), lr=1e-3) 
        elif self.optimizer_str == "AdamW":
            self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=1e-3)
        elif self.optimizer_str == "RMSprop":
            self.optimizer = torch.optim.RMSprop(self.model.parameters(), lr=1e-3)
        
        self.transform = transforms.Compose(
            [
                transforms.Resize([224,224]),
                transforms.ToTensor(),
                transforms.Normalize(
                    # mean=[0.485, 0.456, 0.406], 
                    # std=[0.229, 0.224, 0.225])
                    mean=[0.5, 0.5, 0.5], 
                    std=[0.5, 0.5, 0.5])
            ]
        )

    def read_train_data(self, path): 

        data = datasets.ImageFolder(
            root = path,
            transform = self.transform
        )

        train_rate = 0.9
        num_train_data = round(len(data)*train_rate)
        num_val_data = len(data) - num_train_data
        trainSet, valSet = torch.utils.data.random_split(data, [num_train_data, num_val_data], generator = torch.Generator(device='cuda'))

        self.dataset = {
            'train': trainSet,
            'val': valSet
        }

        self.dataloader = {
            'train': torch.utils.data.DataLoader(
                        dataset = trainSet,
                        batch_size = self.batch_size,
                        shuffle = True,
                        generator=torch.Generator(device='cuda')
                    ),
            'val': torch.utils.data.DataLoader(
                    dataset = valSet,
                    batch_size = self.batch_size,
                    shuffle = True,
                    generator=torch.Generator(device='cuda')
                )
        }
        # print("train:",num_train_data," val:",num_val_data)
        # print('lenth of dataloader[train]:',len(self.dataloader['train']))
        # print('lenth of dataloader[val]:',len(self.dataloader['val']))

    def train(self):

        use_gpu = torch.cuda.is_available()
        # print('use gpu:', use_gpu)

        start_time=time.time()

        self.train_loss = []
        self.train_acc = []
        self.val_loss = []
        self.val_acc = []

        for epoch in range(self.n_epochs):
            since = time.time()
            print("-"*10)
            print("{}, Epoch {}/{}".format(self.modelname, epoch, self.n_epochs))
            for param in ["train", "val"]:
                if param == "train":
                    self.model.train()
                else:
                    self.model.eval()

                running_loss = 0.0
                running_correct = 0 
                batch = 0

                for data in self.dataloader[param]:
                    # print('dataloader[param]=',dataloader[param])
                    batch += 1
                    X, y = data
                    # import ipdb; ipdb.set_trace()
                    if use_gpu:
#                         X, y  = Variable(X.cuda()), Variable(y.cuda())
                        X, y  = Variable(X.cuda()), Variable(y.cuda())
                    else:
                        X, y = Variable(X), Variable(y)
                
                    self.optimizer.zero_grad()
                    y_pred = self.model(X)
                    _, pred = torch.max(y_pred.data, 1)
                    if self.loss == "CE":
                        loss = self.cost(y_pred, y).requires_grad_()
                    else :
                        # print(f"y_pred before squeeze:{y_pred.shape}")
                        y_pred = y_pred.squeeze(1)
                        # print(f"after squeeze:{y_pred.shape}")
                        # print(y.shape)
                        y = y.float()
                        loss = self.cost(y_pred, y)
                    # elif self.loss == "SM":
                    #     loss = self.cost(y_pred, y)

                    if param =="train":
                        loss.backward()
                        self.optimizer.step()

                    running_loss += loss.data
                    running_correct += torch.sum(pred == y.data)

                    if batch%100 == 0 and param =="train":
                        print("Batch {}, Train Loss:{:.4f}, Train ACC:{:.4f}".format(batch, torch.true_divide(running_loss,(self.batch_size*batch)), torch.true_divide(100*running_correct,(self.batch_size*batch))))

                epoch_loss = torch.true_divide(running_loss,len(self.dataset[param])).cpu()
                epoch_correct = torch.true_divide(100*running_correct,len(self.dataset[param])).cpu()

                print("{}  Loss:{:.4f},  Correct:{:.4f}".format(param, epoch_loss, epoch_correct))
                
                if param == "train":
                    self.train_loss.append(epoch_loss)
                    self.train_acc.append(epoch_correct)
                else:
                    self.val_loss.append(epoch_loss) 
                    self.val_acc.append(epoch_correct)

            now_time = time.time() - since   
            print("Training time is:{:.0f}m {:.0f}s".format(now_time//60, now_time%60))

            if epoch % 5 == 0:
                path = f"models/{self.train_mode}/{self.modelname}"
            if not os.path.isdir(path):
                os.makedirs(path)
        now_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        torch.save(self.model, f"{path}/{now_time}_bs_{self.batch_size}_{self.modelname}_op_{self.optimizer_str}_ls_{self.loss}")
        end_time = time.time() - start_time
        print("Total time is:{:.0f}m {:.0f}s".format(end_time//60, end_time%60))

    def plot(self):
        
        fig, ((ax1), (ax2)) = plt.subplots(2, 1, figsize=(20, 10))
        fig.suptitle('{} bs={}'.format(self.modelname, self.batch_size), fontsize=30)

        ax1.plot(range(1,self.n_epochs+1),self.train_loss,label="train loss")
        ax1.plot(range(1,self.n_epochs+1),self.val_loss,label="val loss")
        ax1.set_xlabel("Training Epochs", fontsize=20)
        ax1.set_ylabel("loss", fontsize=25)
        ax1.set_ylim([0, 0.15])
        ax1.tick_params(labelsize=20)
        ax1.legend(loc = 1, prop = {'size':15})

        ax2.plot(range(1,self.n_epochs+1),self.train_acc,label="train accuracy")
        ax2.plot(range(1,self.n_epochs+1),self.val_acc,label="val accuracy")
        ax2.set_xlabel("Training Epochs", fontsize=20)
        ax2.set_ylabel("accuracy", fontsize=25)
        ax2.set_ylim([70, 100])
        ax2.tick_params(labelsize=20)
        ax2.legend(loc = 4, prop = {'size':15})
        path = f'out_put_chart/{self.train_mode}/{self.modelname}/'
        image = f'{path}bs_{self.batch_size}_{self.modelname}_op_{self.optimizer_str}_ls_{self.loss}.png'
        if not os.path.isdir(path):
            os.makedirs(path)
        plt.savefig(image)
        plt.show()
        plt.clf()

        # save params
        # define a list of places
        placesList = [self.train_loss, self.val_loss, self.train_acc, self.val_acc, self.batch_size]
        path = f'out_put_chart/{self.train_mode}/{self.modelname}/bs_{self.batch_size}_{self.modelname}_op_{self.optimizer_str}_ls_{self.loss}.data'
        print(f"save fig at: {path}")
        with open(path, 'wb') as filehandle:
            # store the data as binary data stream
            pickle.dump(placesList, filehandle)

        '''
        import pickle
        with open('/content/drive/My Drive/Colab Notebooks/out_put_chart/bs_{}_1355&929_vgg16.data'.format(batch_size), 'rb') as filehandle:
            # read the data as binary data stream
            placesList = pickle.load(filehandle)
        train_loss, val_loss, train_acc, val_acc, batch_size = placesList[0], placesList[1], placesList[2], placesList[3], placesList[4]
        plot(train_loss, val_loss, train_acc, val_acc, batch_size)
        '''
    def read_model(self,path):
        self.model = torch.load(path)
        self.model.eval()

    def read_list(self, list_path):
        with open(list_path, 'rb') as filehandle:
            # read the data as binary data stream
            placesList = pickle.load(filehandle)
        self.train_loss, self.val_loss, self.train_acc, self.val_acc, self.batch_size\
             = placesList[0], placesList[1], placesList[2], placesList[3], placesList[4]

    def read_test_data(self, path, show=False, print_name=False):
        # load test data
        self.dataset_test_img = datasets.ImageFolder(path, transform = self.transform)
        self.dataloader_test_img = torch.utils.data.DataLoader(dataset=self.dataset_test_img,
                                                               batch_size = 1,
                                                               generator=torch.Generator(device='cuda'),
                                                               shuffle=False)
        if show:
            for batch in self.dataloader_test_img:
                inputs, targets = batch
                for img in inputs:
                    image  = img.cpu().numpy()
                    # transpose image to fit plt input
                    image = image.T
                    # normalise image
                    data_min = np.min(image, axis=(1,2), keepdims=True)
                    data_max = np.max(image, axis=(1,2), keepdims=True)
                    scaled_data = (image - data_min) / (data_max - data_min)
                    # show image
                    plt.imshow(scaled_data)
                    plt.show()
        elif print_name:
            with torch.no_grad():
                for i, (images, labels) in enumerate(self.dataloader_test_img):
                    sample_fname, _ = self.dataloader_test_img.dataset.samples[i]
                    print(f'{i},{sample_fname}')

    def show_images(self, images, nmax=64):
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_xticks([]); ax.set_yticks([])
        ax.imshow(make_grid((images[:nmax]), nrow=8).permute(1, 2, 0))

    def show_batch(self, dl, nmax=64):
        for images in dl:
            self.show_images(images, nmax)
            break
    def test(self):
        # testing
        # "/content/drive/My Drive/Colab Notebooks/models/bs_100/eph_15_bs_100_1355&929_vgg16_finetune"
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0
        prediction = []
        count = 0
        for i, (image, label) in enumerate(self.dataloader_test_img):

            images = Variable(image.cuda())
            labels = Variable(label.cuda())

            y_pred = self.model(images)
            
            _, pred = torch.max(y_pred.data, 1)
            prediction += pred.tolist() 
            img = torchvision.utils.make_grid(image,nrow=24)
            img = img.numpy().transpose(1,2,0)

            mean = [0.5,0.5,0.5]
            std  = [0.5,0.5,0.5]
            img = img*std+mean
            # if i == 0:
            # print(f"label: {label}")
            # print(f"predi: {pred}")
            # plt.figure(figsize=(30,20))
            # plt.imshow(img)


            """ confusion matrix:
            Returns the confusion matrix for the values in the `prediction` and `truth`
            tensors, i.e. the amount of positions where the values of `prediction`
            and `truth` are
            - 1 and 1 (True Positive)
            - 1 and 0 (False Positive)
            - 0 and 0 (True Negative)
            - 0 and 1 (False Negative)
            """

            confusion_vector = torch.true_divide( pred, label)
            # Element-wise division of the 2 tensors returns a new tensor which holds a
            # unique value for each case:
            #   1     where prediction and truth are 1 (True Positive)
            #   inf   where prediction is 1 and truth is 0 (False Positive)
            #   nan   where prediction and truth are 0 (True Negative)
            #   0     where prediction is 0 and truth is 1 (False Negative)

            true_positives += torch.sum(confusion_vector == 1).item()
            false_positives += torch.sum(confusion_vector == float('inf')).item()
            true_negatives += torch.sum(torch.isnan(confusion_vector)).item()
            false_negatives += torch.sum(confusion_vector == 0).item()
        if (true_positives+false_positives+true_negatives+false_negatives) != 0:
            self.accuracy = (true_positives + true_negatives) / (true_positives+false_positives+true_negatives+false_negatives)
        else:
            self.accuracy = 0
        if (true_positives + false_negatives) != 0 :
            self.recall = true_positives / (true_positives + false_negatives)
        else:
            self.recall = 0
        if (true_positives + false_positives) != 0:
            self.precision = true_positives / (true_positives + false_positives)
        else:
            self.precision = 0
        if  (self.precision + self.recall) != 0:
            self.f1_score = 2 * self.precision * self.recall / (self.precision + self.recall)
        else:
            self.f1_score = 0
        
        print("TP:", true_positives, "| FP:", false_positives, "| TN:", true_negatives, "| FN:", false_negatives)
        print("accuracy:{:.3f}".format(self.accuracy), "recall:{:.3f}".format(self.recall), "| precision:{:.3f}".format(self.precision), "| f1_score:{:.3f}".format(self.f1_score))
        return self.accuracy, self.recall, self.precision, self.f1_score, prediction
