from manager import \
    IoTHubRegistryManager, \
    receive_twin_reported, \
    clear_desired_twin,process_production,\
    asyncio, os,load_dotenv,get_most_recent_blob, receive_device_ids, \
    BlobServiceClient, run_res_error, process_error_dm, send_device_connection_keys
import sys
from datetime import datetime
import aioconsole

load_dotenv()
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
CONNECTION_STRING_MANAGER = os.getenv("CONNECTION_STRING_MANAGER")
DEVICE_ID = os.getenv("DEVICE_ID")
KPI_CONTAINER_NAME = os.getenv('KPI_CONTAINER_NAME')
ERROR_CONTAINER_NAME = os.getenv('ERROR_CONTAINER_NAME')
productionLine = ['OPCUA_Device_1_irctm3', 'OPCUA_Device_2_dqfv7p']
async def main():
    registry_manager = IoTHubRegistryManager(CONNECTION_STRING_MANAGER)
    productionLine, connection_strs= await receive_device_ids(registry_manager)
    try:
        await send_device_connection_keys(connection_strs)
    except Exception as send_e:
        print(f"error when sending a message to service bus")
    for device in productionLine:
        await clear_desired_twin(registry_manager, device)
    
    blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
    kpi_last_processed_name  = None
    error_last_processed_name = None
    kpi_last_processed_time = datetime.min 
    error_last_processed_time = datetime.min 
    err_last_positions = {}
    kpi_last_positions = {}
    try:
        while True:      
            for device in productionLine:  
                twin_reported = await receive_twin_reported(registry_manager, device)
            kpi_container_name = KPI_CONTAINER_NAME
            kpi_container_client = blob_service_client.get_container_client(kpi_container_name)
            error_container_name = ERROR_CONTAINER_NAME
            error_container_client = blob_service_client.get_container_client(error_container_name)

            for device in productionLine:  
                await run_res_error(registry_manager, device)
            
            try:
                new_data1, kpi_last_processed_name, kpi_last_processed_time, kpi_last_positions = await get_most_recent_blob(kpi_container_client, kpi_last_processed_name, kpi_last_processed_time, kpi_last_positions)
                if new_data1:
                    await process_production(registry_manager, new_data1, productionLine)
                    #print(f"New data from blob {kpi_last_processed_name} arrived")
                else:
                    print("No new data found")
            except Exception as e:
                print(f"Exception with Kpi Profuction Container process: {e}")

            error_devices=[]
            try:
                new_data, error_last_processed_name, error_last_processed_time, err_last_positions = await get_most_recent_blob(error_container_client, error_last_processed_name, error_last_processed_time, err_last_positions)
                if new_data:
                    error_devices = await process_error_dm(registry_manager, new_data, productionLine)
                    #print(f"New data from blob {error_last_processed_name} arrived")
                else:
                    print("No new data found")
                
                #You can reset error on a device if it was stopped
                if error_devices:
                    answer = "empty"
                    while answer.lower() != "no":
                        answer = await aioconsole.ainput(f"Reset error status for device(s) {error_devices}? (No/device name): ")
                        if answer.lower() != "no":
                            await run_res_error(registry_manager, answer)
            except Exception as ee:
                print(f"Exception with Error Container process: {ee}")
            await asyncio.sleep(60)
                 

    except Exception as e:
        print("Progam stoped")
        print(f"Error: {e}")
        sys.exit(1)
if __name__ == "__main__":
    asyncio.run(main())