import os
import nacos


def nacos_register():
    if not os.getenv("NACOS_SERVER_ADDRESS"):
        return
    try:
        client = nacos.NacosClient(
            server_addresses=os.getenv("NACOS_SERVER_ADDRESS"),
            namespace=os.getenv("NACOS_NAMESPACE_ID"),
            username=os.getenv("NACOS_USERNAME"),
            password=os.getenv("NACOS_PASSWORD"),
        )

        client.add_naming_instance(
            os.getenv("NACOS_SERVER_NAME"),
            os.getenv("NACOS_SERVER_HOST"),
            os.getenv("NACOS_SERVER_PORT"),
            cluster_name="DEFAULT",
            weight=1.0,
            metadata={"version": "1.0.0"},
            ephemeral=True,
        )
    except Exception as e:
        print(f"Failed to register server to Nacos: {e}")
