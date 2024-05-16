from flask import Flask, request, render_template, redirect, url_for, flash
import xarray as xr
import numpy as np
import os
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists('static'):
    os.makedirs('static')

def mean_absolute_error(obs, model):
    return np.mean(np.abs(obs - model))

def root_mean_square_error(obs, model):
    return np.sqrt(np.mean((obs - model)**2))

def anomaly_correlation_coefficient(obs, model):
    obs_anomaly = obs - np.mean(obs)
    model_anomaly = model - np.mean(model)
    return np.corrcoef(obs_anomaly, model_anomaly)[0, 1]

def generate_spatial_plot(obs, model):
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))

    obs_plot = obs.mean(dim='time').plot(ax=axes[0], add_colorbar=True)
    axes[0].set_title('Observed Data (Mean)')

    model_plot = model.mean(dim='time').plot(ax=axes[1], add_colorbar=True)
    axes[1].set_title('Model Data (Mean)')

    plt.tight_layout()
    plot_path = os.path.join('static', 'spatial_plot.png')
    plt.savefig(plot_path)
    plt.close(fig)
    return plot_path

def generate_time_series_plot(obs, model, start_lat, stop_lat, start_lon, stop_lon):
    obs_series = obs.sel(lat=slice(start_lat, stop_lat), lon=slice(start_lon, stop_lon)).mean(dim=['lat', 'lon'])
    model_series = model.sel(lat=slice(start_lat, stop_lat), lon=slice(start_lon, stop_lon)).mean(dim=['lat', 'lon'])

    fig, ax = plt.subplots(figsize=(10, 5))

    obs_series.plot(ax=ax, label='Observed Data')
    model_series.plot(ax=ax, label='Model Data')

    ax.set_title('Time Series Comparison')
    ax.legend()

    plot_path = os.path.join('static', 'time_series_plot.png')
    plt.savefig(plot_path)
    plt.close(fig)
    return plot_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compute', methods=['POST'])
def compute_metrics():
    try:
        obs_data_file = request.files['obs_data']
        model_data_file = request.files['model_data']
        metrics = request.form.getlist('metrics')
        plot_type = request.form.get('plotType', None)
        start_lat = float(request.form.get('startLatitude', 0))
        stop_lat = float(request.form.get('stopLatitude', 0))
        start_lon = float(request.form.get('startLongitude', 0))
        stop_lon = float(request.form.get('stopLongitude', 0))

        if not obs_data_file or not model_data_file or not metrics:
            flash('Please upload both data files and select at least one metric.')
            return redirect(url_for('index'))

        obs_data_path = os.path.join(app.config['UPLOAD_FOLDER'], obs_data_file.filename)
        model_data_path = os.path.join(app.config['UPLOAD_FOLDER'], model_data_file.filename)

        obs_data_file.save(obs_data_path)
        model_data_file.save(model_data_path)

        obs_data = xr.open_dataarray(obs_data_path)
        model_data = xr.open_dataarray(model_data_path)

        if obs_data is None or model_data is None:
            flash('Error loading data files.')
            return redirect(url_for('index'))

        results = {}
        if 'MeanAbsoluteError' in metrics:
            results['MAE'] = mean_absolute_error(obs_data.values, model_data.values)
        if 'RootMeanSquareError' in metrics:
            results['RMSE'] = root_mean_square_error(obs_data.values, model_data.values)
        if 'AnomalyCorrelationCoefficient' in metrics:
            results['ACC'] = anomaly_correlation_coefficient(obs_data.values, model_data.values)

        plot_path = None
        if plot_type == 'spatial':
            plot_path = generate_spatial_plot(obs_data, model_data)
        elif plot_type == 'timeSeries':
            plot_path = generate_time_series_plot(obs_data, model_data, start_lat, stop_lat, start_lon, stop_lon)

        if not results and not plot_path:
            flash('No results computed. Please check the input data and metrics.')
            return redirect(url_for('index'))

        return render_template('results.html', results=results, plot_path=plot_path)
    except KeyError as e:
        flash(f'Missing form field: {e}')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'An error occurred: {e}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
