import numpy as np
import math
import matplotlib as mpl
from matplotlib.image import imread
from random import randint

# import theano
import keras
import pandas

from keras.models import Sequential
from keras.layers import Dense, Activation, LSTM, Dropout
# from keras.wrappers.scikit_learn import KerasClassifier
from scikeras.wrappers import KerasClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.tree import DecisionTreeRegressor
from keras import optimizers
from keras.optimizers import RMSprop
import keras.utils
import keras.layers
from sklearn.model_selection import KFold
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import AdaBoostClassifier
from sklearn.ensemble import AdaBoostRegressor
import copy
import csv


mpl.use('Agg')
import matplotlib.pyplot as plt

#Set y values of data to lie between 0 and 1
def normalize_data(dataset, data_min, data_max):
    data_std = (dataset - data_min) / (data_max - data_min)
    test_scaled = data_std * (np.amax(data_std) - np.amin(data_std)) + np.amin(data_std)
    return test_scaled

#Import and pre-process data for future applications
def import_data(train_dataframe, dev_dataframe, test_dataframe):
    dataset = train_dataframe.values
    dataset = dataset.astype('float32')

    #Include all 12 initial factors (Year ; Month ; Hour ; Day ; Cloud Coverage ; Visibility ; Temperature ; Dew Point ;
    #Relative Humidity ; Wind Speed ; Station Pressure ; Altimeter
    max_test = np.max(dataset[:,12])
    min_test = np.min(dataset[:,12])
    scale_factor = max_test - min_test
    max = np.empty(13)
    min = np.empty(13)

    #Create training dataset
    for i in range(0,13):
        min[i] = np.amin(dataset[:,i],axis = 0)
        max[i] = np.amax(dataset[:,i],axis = 0)
        dataset[:,i] = normalize_data(dataset[:, i], min[i], max[i])

    train_data = dataset[:,0:12]
    train_labels = dataset[:,12]

    # Create dev dataset
    dataset = dev_dataframe.values
    dataset = dataset.astype('float32')

    for i in range(0, 13):
        dataset[:, i] = normalize_data(dataset[:, i], min[i], max[i])

    dev_data = dataset[:,0:12]
    dev_labels = dataset[:,12]

    # Create test dataset
    dataset = test_dataframe.values
    dataset = dataset.astype('float32')

    for i in range(0, 13):
        dataset[:, i] = normalize_data(dataset[:, i], min[i], max[i])

    test_data = dataset[:, 0:12]
    test_labels = dataset[:, 12]

    return train_data, train_labels, dev_data, dev_labels, test_data, test_labels, scale_factor

#Construt and return Keras RNN model
# def build_model(init_type='glorot_uniform', optimizer='adam'):
#     model = Sequential()
#     layers = [12, 64, 64, 1, 1]
#     model.add(keras.layers.LSTM(
#         layers[0],
#         input_shape = (None,12),
#         return_sequences=True))
#     model.add(keras.layers.Dropout(0.2))

#     model.add(keras.layers.LSTM(
#         layers[1],
#         kernel_initializer = init_type,
#         return_sequences=True
#         #bias_initializer = 'zeros'
#     ))
#     model.add(keras.layers.Dropout(0.2))

#     model.add(Dense(
#         layers[2], activation='tanh',
#         kernel_initializer=init_type,
#         input_shape = (None,1)
#         ))
#     model.add(Dense(
#         layers[3]))

#     model.add(Activation("relu"))

#     #Alternative parameters:
#     #momentum = 0.8
#     #learning_rate = 0.1
#     #epochs = 100
#     #decay_rate = learning_rate / 100
#     #sgd = keras.optimizers.SGD(lr=learning_rate, momentum=momentum, decay=decay_rate, nesterov=False)
#     #model.compile(loss="binary_crossentropy", optimizer=sgd)
#     rms = keras.optimizers.RMSprop(lr=0.002, rho=0.9, epsilon=1e-08, decay=0.01)
#     model.compile(loss="mean_squared_error", optimizer=optimizer)

#     return model

def build_model(init_type='glorot_uniform'):
    model = Sequential([
        LSTM(12, kernel_initializer=init_type, return_sequences=True, input_shape=(1, 12)),
        Dropout(0.2),  
        LSTM(64, kernel_initializer=init_type, return_sequences=True),
        Dropout(0.2),
        Dense(64, activation='tanh', kernel_initializer=init_type),
        Dense(1),
        Activation("relu")
    ])
    
    optimizer = RMSprop(learning_rate=0.001, rho=0.9, epsilon=1e-08) # reduce learning rate
    model.compile(loss="mean_squared_error", optimizer=optimizer)
    return model

#Save output predictions for graphing and inspection
def write_to_csv(prediction, filename):
    print("Writing to CSV...")
    with open(filename, 'w') as file:
        for i in range(prediction.shape[0]):
            file.write("%.5f" % prediction[i][0][0])
            file.write('\n')
    print("...finished!")

#Return MSE error values of all three data sets based on a single model
def evaluate(model, X_train, Y_train, X_dev, Y_dev, X_test, Y_test, scale_factor):
    scores = model.evaluate(X_train, Y_train, verbose = 0) * scale_factor * scale_factor
    print("train: ", model.metrics_names, ": ", scores)
    scores = model.evaluate(X_dev, Y_dev, verbose = 0) * scale_factor * scale_factor
    print("dev: ", model.metrics_names, ": ", scores)
    scores = model.evaluate(X_test, Y_test, verbose = 0) * scale_factor * scale_factor
    print("test: ", model.metrics_names, ": ", scores)

#Calculate MSE between two arrays of values
def mse(predicted, observed):
    return np.sum(np.multiply((predicted - observed),(predicted - observed)))/predicted.shape[0]

def main():
    plt.switch_backend('tkAgg')

    #Import test data (6027, 13)
    train_dataframe = pandas.read_csv('weather_train.csv', sep=";", engine='python', header=None)
    dev_dataframe = pandas.read_csv('weather_dev.csv', sep=";", engine='python', header=None)
    test_dataframe = pandas.read_csv('weather_test.csv', sep=";", engine='python', header=None)

    train_data, train_labels, dev_data, dev_labels, test_data, test_labels, scale_factor = import_data(train_dataframe, dev_dataframe, test_dataframe)

    # Reshape data for LSTM model
    X_train_lstm = np.reshape(train_data, (train_data.shape[0], 1, train_data.shape[1]))
    X_dev_lstm = np.reshape(dev_data, (dev_data.shape[0], 1, dev_data.shape[1]))
    X_test_lstm = np.reshape(test_data, (test_data.shape[0], 1, test_data.shape[1]))
    Y_train_lstm = np.reshape(train_labels, (train_labels.shape[0], 1, 1))
    Y_dev_lstm = np.reshape(dev_labels, (dev_labels.shape[0], 1, 1))
    Y_test_lstm = np.reshape(test_labels, (test_labels.shape[0], 1, 1))

    # LSTM model training and prediction
    model = build_model('glorot_uniform')
    model.fit(X_train_lstm, Y_train_lstm, batch_size=32, epochs=150)  # larger batch size and more epochs
    trainset_predicted_lstm = model.predict(X_train_lstm)
    devset_predicted_lstm = model.predict(X_dev_lstm)
    testset_predicted_lstm = model.predict(X_test_lstm)

    #Adaboost model (ensemble learning)
    adaboost = AdaBoostRegressor(n_estimators=50, learning_rate=0.005, loss='linear') # decreased learning rate
    adaboost.fit(train_data, train_labels) 

    # Prediction using AdaBoost
    trainset_predicted_ada = adaboost.predict(train_data)
    devset_predicted_ada = adaboost.predict(dev_data)
    testset_predicted_ada = adaboost.predict(test_data)

    # Evaluate or use your predictions as needed
    print("Train MSE LSTM: ", mse(trainset_predicted_lstm, Y_train_lstm) * scale_factor * scale_factor)
    print("Dev MSE LSTM: ", mse(devset_predicted_lstm, Y_dev_lstm) * scale_factor * scale_factor)
    print("Test MSE LSTM: ", mse(testset_predicted_lstm, Y_test_lstm) * scale_factor * scale_factor)

    print("Train MSE AdaBoost: ", mse(trainset_predicted_ada, train_labels) * scale_factor * scale_factor)
    print("Dev MSE AdaBoost: ", mse(devset_predicted_ada, dev_labels) * scale_factor * scale_factor)
    print("Test MSE AdaBoost: ", mse(testset_predicted_ada, test_labels) * scale_factor * scale_factor)


    # # K-fold cross validation (K = 10):
    # kf = KFold(n_splits=10, shuffle=True)
    # # Loop through the indices the split() method returns
    # for index, (train_indices, val_indices) in enumerate(kf.split(X_train, Y_train)):
    #     print("Training on fold " + str(index + 1) + "/10...")
    #     # Generate batches from indices
    #     xtrain, xval = X_train[train_indices], X_train[val_indices]
    #     ytrain, yval = Y_train[train_indices], Y_train[val_indices]
    #     # Clear model, and create it
    #     model = None
    #     model = build_model()

    #     model.fit(
    #         xtrain, ytrain,
    #         batch_size=16, epochs=model_fit_epochs)
    #     testset_predicted = model.predict(xval)
    #     print("Test MSE: ", mse(testset_predicted, yval))

    # #Grid search to optimize model params

    # init = ['glorot_uniform', 'normal', 'uniform']
    # epochs = [50, 100, 150]
    # batches = [8, 16, 32]
    # optimizers = ['rmsprop', 'adam', 'adaboost']
    # optimal_params = np.empty(4)
    # minimum_error = 2e63

    # for init_type in init:
    #     for epoch in epochs:
    #         for batch in batches:
    #             for optimizer in optimizers:
    #                 model = None
    #                 model = build_model(init_type, optimizer)

    #                 model.fit(
    #                     X_train, Y_train,
    #                     batch_size=batch, epochs=epoch)
    #                 predicted = model.predict(X_test)
    #                 error = mse(predicted, Y_test)
    #                 if error < minimum_error:
    #                     error = minimum_error
    #                     optimal_params = [init_type, epoch, batch, optimizer]

    # print("optimal params: ", optimal_params)
    # print("minimized error: ", minimum_error)

    # write_to_csv(trainset_predicted_lstm,'lstm_trainset_prediction.csv')
    # write_to_csv(devset_predicted_lstm,'lstm_devset_prediction.csv')
    # write_to_csv(testset_predicted_lstm, 'lstm_testset_prediction.csv')
    # write_to_csv(trainset_predicted_ada,'ada_trainset_prediction.csv')
    # write_to_csv(devset_predicted_ada,'ada_devset_prediction.csv')
    # write_to_csv(testset_predicted_ada, 'ada_testset_prediction.csv')
    return

if __name__ == '__main__':
    main()