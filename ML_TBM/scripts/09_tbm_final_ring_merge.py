import pandas as pd

# Load datasets
df_p = pd.read_csv(r"D:\%PRACA_MAGISTERSKA\data\interim\ring_tbm_machine_params.csv")
df_c = pd.read_csv(r"D:\%PRACA_MAGISTERSKA\data\interim\ring_tbm_coords.csv")

# Join based on 'ring' only (timestamp is taken from TBM parameters)
df_final = pd.merge(df_p, df_c[['ring', 'lat_center', 'lon_center']], on='ring', how='inner')

# Rename coordinate columns for database consistency
df_final = df_final.rename(columns={'lat_center': 'latitude', 'lon_center': 'longitude'})

# Ensure ISO format for SQL compatibility
df_final['timestamp'] = pd.to_datetime(df_final['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

# Define column order according to SQL schema
cols = ['ring', 'timestamp', 'serial_number', 'latitude', 'longitude', 
        'epb_avg', 'epb_min', 'epb_max', 'torque_avg', 'torque_min', 'torque_max', 
        'thrust_avg', 'thrust_min', 'thrust_max', 'soil_exc_density_avg', 
        'soil_exc_volume', 'soil_exc_weight', 'grout_expected', 'grout_injected', 
        'foam_poly_vol', 'foam_poly_weight', 'foam_surf_vol', 'foam_surf_weight', 
        'foam_water_vol', 'bentonite_vol', 'bentonite_weight', 'cond_soil_vol_v6', 
        'cond_soil_sum_vol', 'cond_soil_sum_weight', 'muck_density', 
        'soil_category', 'soil_description']

# Save final processed file
df_final[cols].to_csv(r"D:\%PRACA_MAGISTERSKA\data\interim\tbm_telemetry_final_ring.csv", index=False)
print("Final file ready. You can now import it into SQL.")