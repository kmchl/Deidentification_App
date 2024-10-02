# utils.py

import streamlit as st
import pandas as pd
import tempfile
import os
from src.data_processing import DataProcessor
import matplotlib.pyplot as plt
import traceback
from src.binning import DensityPlotter
from src.binning import DataIntegrityAssessor
from src.binning import UniqueBinIdentifier
from src.config import PROCESSED_DATA_DIR, REPORTS_DIR, PLOTS_DIR, UNIQUE_IDENTIFICATIONS_DIR, CAT_MAPPING_DIR, DATA_DIR


def hide_streamlit_style():
    """
    Hides Streamlit's default menu and footer for a cleaner interface.
    """
    hide_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """
    st.markdown(hide_style, unsafe_allow_html=True)

def run_processing(save_type='csv', output_filename='Processed_Data.csv', file_path='Data.csv'):
    """
    Initializes and runs the data processor, saving outputs to the designated directories.
    """
    try:
        # Define output file paths
        output_filepath = os.path.join(PROCESSED_DATA_DIR, output_filename)
        report_path = os.path.join(REPORTS_DIR, 'Type_Conversion_Report.csv')
        
        processor = DataProcessor(
            input_filepath=os.path.join(DATA_DIR, file_path),
            output_filepath=output_filepath,
            report_path=report_path,
            return_category_mappings=True,
            mapping_directory=CAT_MAPPING_DIR,
            parallel_processing=False,
            date_threshold=0.6,
            numeric_threshold=0.9,
            factor_threshold_ratio=0.2,
            factor_threshold_unique=1000,
            dayfirst=True,
            log_level='INFO',
            log_file=None,
            convert_factors_to_int=True,
            date_format=None,  # Keep as None to retain datetime dtype
            save_type=save_type
        )
        processed_data = processor.process()
        return processed_data
        
    except Exception as e:
        st.error(f"Error during data processing: {e}")
        st.stop()

def load_data(file_type, uploaded_file):
    """
    Loads the uploaded file into a Pandas DataFrame without any processing.

    Parameters:
        file_type (str): Type of the uploaded file ('csv' or 'pkl').
        uploaded_file (UploadedFile): The uploaded file object.

    Returns:
        pd.DataFrame: The loaded DataFrame.
        str: Error message if any, else None.
    """
    if uploaded_file is None:
        return None, "No file uploaded!"

    try:
        # Determine the appropriate file extension
        file_extension = {
            "pkl": "pkl",
            "csv": "csv"
        }.get(file_type, "csv")  # Default to 'csv' if type is unrecognized

        # Create a temporary file with the correct extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            temp_file_path = tmp_file.name

        # Read the data into a DataFrame
        if file_type == "pkl":
            Data = pd.read_pickle(temp_file_path)
        elif file_type == "csv":
            Data = pd.read_csv(temp_file_path)
        else:
            return None, "Unsupported file type!"

        # Clean up temporary file
        os.remove(temp_file_path)

        return Data, None
    except Exception as e:
        return None, f"Error loading data: {e}"

def align_dataframes(original_df, binned_df):
    """
    Ensures both DataFrames have the same columns.
    """
    try:
        # Identify columns that exist in the original DataFrame but not in the binned DataFrame
        missing_in_binned = original_df.columns.difference(binned_df.columns)
        
        # Retain all original columns that were not binned in the binned DataFrame
        for column in missing_in_binned:
            binned_df[column] = original_df[column]
        
        # Ensure columns are ordered the same way
        binned_df = binned_df[original_df.columns]
        
        return original_df, binned_df
    except Exception as e:
        st.error(f"Error aligning dataframes: {e}")
        st.stop()

def save_dataframe(df, file_type, filename, subdirectory):
    """
    Saves the DataFrame to the specified file type within a subdirectory.
    """
    try:
        
        # Determine the full path
        if subdirectory == "processed_data":
            dir_path = PROCESSED_DATA_DIR
        elif subdirectory == "reports":
            dir_path = REPORTS_DIR
        elif subdirectory == "unique_identifications":
            dir_path = UNIQUE_IDENTIFICATIONS_DIR
        elif subdirectory == "plots":
            dir_path = PLOTS_DIR
        else:
            raise ValueError("Unsupported subdirectory for saving DataFrame.")

        file_path = os.path.join(dir_path, filename)

        if file_type == 'csv':
            df.to_csv(file_path, index=False)
        elif file_type == 'pkl':
            df.to_pickle(file_path)
        else:
            raise ValueError("Unsupported file type for saving.")
        
        return file_path  # Return the path for further use if needed
    except Exception as e:
        st.error(f"Error saving DataFrame: {e}")
        st.stop()

def load_dataframe(file_path, file_type):
    """
    Loads a DataFrame from the specified file path and type.
    """
    try:
        if file_type == 'csv':
            return pd.read_csv(file_path)
        elif file_type == 'pkl':
            return pd.read_pickle(file_path)
        else:
            raise ValueError("Unsupported file type for loading.")
    except Exception as e:
        st.error(f"Error loading DataFrame: {e}")
        st.stop()

def get_binning_configuration(Data, selected_columns_binning):
    """
    Generates binning configuration sliders for selected columns.
    """
    bins = {}
    st.markdown("### 📏 Binning Configuration")

    for column in selected_columns_binning:
        max_bins = Data[column].nunique()
        min_bins = 2 if max_bins >= 2 else 1  # At least 2 bins if possible
        default_bins = min(10, max_bins) if max_bins >= 2 else 1  # Default to 10 or max_unique if lower

        bins[column] = st.slider(
            f'📏 {column}', 
            min_value=1, 
            max_value=max_bins, 
            value=default_bins, 
            key=f'bin_slider_{column}'
        )
    
    return bins


def plot_entropy_and_display(assessor, plots_dir):
    """
    Plots the entropy and displays it in Streamlit.

    Args:
        assessor (DataIntegrityAssessor): The integrity assessor instance.
        plots_dir (str): Directory to save the entropy plot.
    """
    st.markdown("### 📈 Entropy")
    try:
        fig_entropy = assessor.plot_entropy(figsize=(15, 4))  # Create the entropy plot
        # Save the entropy plot
        entropy_plot_path = os.path.join(plots_dir, 'entropy_plot.png')
        fig_entropy.savefig(entropy_plot_path, bbox_inches='tight')
        # Display in Streamlit before closing
        st.pyplot(fig_entropy)  # to display
        plt.close(fig_entropy)  # Close the figure to free memory
    except Exception as e:
        st.error(f"Error plotting entropy: {e}")
        st.error(traceback.format_exc())  # Detailed error log

def plot_density_plots_and_display(original_df, binned_df, selected_columns_binning, plots_dir):
    """
    Plots the density plots for original and binned data and displays them in Streamlit.

    Args:
        original_df (pd.DataFrame): Original DataFrame for assessment.
        binned_df (pd.DataFrame): Binned DataFrame for assessment.
        selected_columns_binning (list): Columns selected for binning.
        plots_dir (str): Directory to save the density plots.
    """
    st.markdown("### 📈 Density Plots")
    if len(selected_columns_binning) > 1:
        density_tab1, density_tab2 = st.tabs(["Original Data", "Binned Data"])
        
        with density_tab1:
            try:
                plotter_orig = DensityPlotter(
                    dataframe=original_df,  # Use original categorical data
                    category_columns=selected_columns_binning,
                    figsize=(15, 4),                     
                    save_path=None,  # We'll handle saving manually
                    plot_style='ticks'
                )
                
                fig_orig = plotter_orig.plot_grid()
                # Save the plot
                original_density_plot_path = os.path.join(plots_dir, 'original_density_plots.png')
                fig_orig.savefig(original_density_plot_path, bbox_inches='tight')
                # Display before closing
                st.pyplot(fig_orig)
                plt.close(fig_orig)
            except Exception as e:
                st.error(f"Error plotting original data density: {e}")
                st.error(traceback.format_exc())  # Detailed error log

        with density_tab2:
            try:
                plotter_binned = DensityPlotter(
                    dataframe=binned_df,  # Use user-specified binned data
                    category_columns=selected_columns_binning,
                    figsize=(15, 4),                     
                    save_path=None,  # We'll handle saving manually
                    plot_style='ticks'
                )
                fig_binned = plotter_binned.plot_grid()
                # Save the plot
                binned_density_plot_path = os.path.join(plots_dir, 'binned_density_plots.png')
                fig_binned.savefig(binned_density_plot_path, bbox_inches='tight')
                # Display before closing
                st.pyplot(fig_binned)
                plt.close(fig_binned)
            except Exception as e:
                st.error(f"Error plotting binned data density: {e}")
                st.error(traceback.format_exc())  # Detailed error log
    else:
        # Print a message if only one column is selected
        st.info("🔄 **Please select more than one column to display density plots.**")

def handle_download_binned_data(data, file_type_download='csv', save_dataframe_func=save_dataframe):
    """
    Handles the download functionality for binned data.

    Args:
        data (pd.DataFrame): The binned DataFrame to be downloaded.
        file_type_download (str): The selected file type for download ('csv' or 'pkl').
        save_dataframe_func (callable): Function to save the DataFrame.
        plots_dir (str): Directory to save any related plots if necessary.
    """

    st.markdown("### 💾 Download Binned Data")
    try:
        if file_type_download == 'csv':
            binned_csv = data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Binned Data as CSV",
                data=binned_csv,
                file_name='binned_data.csv',
                mime='text/csv',
            )
        elif file_type_download == 'pkl':
            # Save pickle to the 'processed_data' directory
            pickle_filename = 'binned_data.pkl'
            pickle_path = save_dataframe_func(data, 'pkl', pickle_filename, 'processed_data')
            
            with open(pickle_path, 'rb') as f:
                binned_pkl = f.read()
            
            st.download_button(
                label="📥 Download Binned Data as Pickle",
                data=binned_pkl,
                file_name='binned_data.pkl',
                mime='application/octet-stream',
            )
    except Exception as e:
        st.error(f"Error during data download: {e}")
        st.error(traceback.format_exc())  # Detailed error log

def handle_integrity_assessment(original_df, binned_df, plots_dir):
    """
    Handles the integrity assessment process, including generating reports and plotting entropy.

    Args:
        original_df (pd.DataFrame): Original DataFrame for assessment.
        binned_df (pd.DataFrame): Binned DataFrame for assessment.
        plots_dir (str): Directory to save plots.

    Returns:
        None
    """

    try:
        assessor = DataIntegrityAssessor(original_df=original_df, binned_df=binned_df)
        assessor.assess_integrity_loss()
        report = assessor.generate_report()
        
        # Save the report to the 'reports' directory
        report_filename = 'Integrity_Loss_Report.csv'
        save_dataframe(report, 'csv', report_filename, 'reports')
        
        overall_loss = assessor.get_overall_loss()

        st.markdown("### 📄 Integrity Loss Report")
        st.dataframe(report)
        st.write(f"📊 **Overall Average Integrity Loss:** {overall_loss:.2f}%")

        # Plot and display entropy using utility function
        plot_entropy_and_display(assessor, plots_dir)


    except Exception as e:
        st.error(f"Error during integrity assessment: {e}")
        st.error(traceback.format_exc())  # Detailed error log
    
    

def handle_unique_identification_analysis(original_df, binned_df, columns_list, min_comb_size, max_comb_size):
    """
    Handles the unique identification analysis process, including progress updates, result display, and downloads.

    Args:
        original_df (pd.DataFrame): Original DataFrame for analysis.
        binned_df (pd.DataFrame): Binned DataFrame for analysis.
        bin_columns_list (list): List of bin columns to consider.
        min_comb_size (int): Minimum combination size.
        max_comb_size (int): Maximum combination size.

    Returns:
        pd.DataFrame: Results of the unique identification analysis.
    """
    try:
        with st.spinner('🔍 Analyzing unique identifications... This may take a while for large datasets.'):
            
            progress_bar = st.progress(0)
            def update_progress(combination_counter, total_combinations):
                progress = combination_counter / total_combinations
                st.session_state.progress = min(progress, 1.0)
                progress_bar.progress(st.session_state.progress)
            
            # Initialize the UniqueBinIdentifier
            identifier = UniqueBinIdentifier(original_df=original_df, binned_df=binned_df)                    
            # Perform unique identification analysis
            results = identifier.find_unique_identifications(
                min_comb_size=min_comb_size, 
                max_comb_size=max_comb_size, 
                columns=columns_list,
                progress_callback=update_progress
            )
            progress_bar.empty()
            
            return results
    except Exception as e:
        st.error(f"Error during unique identification analysis: {e}")
        st.error(traceback.format_exc())  # Detailed error log
        return None

def display_unique_identification_results(results):
    """
    Displays the unique identification analysis results and provides download options.

    Args:
        results (pd.DataFrame): Results of the unique identification analysis.

    Returns:
        None
    """
    if results is not None:
        # Display the results
        st.success("✅ Unique Identification Analysis Completed!")
        st.write("📄 **Unique Identification Results:**")
        st.dataframe(results) 
        
        # Save the results to 'unique_identifications' directory
        unique_id_filename = 'unique_identifications.csv'
        unique_id_path = save_dataframe(results, 'csv', unique_id_filename, 'unique_identifications')
        
        # Allow user to download the results
        csv = results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name='unique_identifications.csv',
            mime='text/csv',
        )