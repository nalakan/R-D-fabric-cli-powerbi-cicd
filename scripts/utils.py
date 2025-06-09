import os
import shutil
import subprocess
import re
import json

def fab_authenticate_spn(client_id: str = None, client_secret: str = None, tenant_id: str = None):
    print("Authenticating with SPN")

    if client_id is None or client_secret is None or tenant_id is None:
        client_id = os.getenv("FABRIC_CLIENT_ID")
        client_secret = os.getenv("FABRIC_CLIENT_SECRET")
        tenant_id = os.getenv("FABRIC_TENANT_ID")

    if not tenant_id or not client_id or not client_secret:
        raise Exception(
            "Environment variables FABRIC_CLIENT_ID, FABRIC_CLIENT_SECRET and FABRIC_TENANT_ID must be set"
        )

    run_fab_command("config set fab_encryption_fallback_enabled true")
    run_fab_command(
        f"auth login -u {client_id} -p {client_secret} --tenant {tenant_id}",
        include_secrets=True,
    )


def run_fab_command(command, capture_output: bool = False, include_secrets: bool = False, silently_continue: bool = False):
    result = subprocess.run(
        ["fab", "-c", command], capture_output=capture_output, text=True
    )

    if not silently_continue and (result.returncode > 0 or result.stderr):
        raise Exception(
            f"Error running fab command. exit_code: '{result.returncode}'; stderr: '{result.stderr}'"
        )

    if capture_output:
        return result.stdout.strip().split("\n")[-1]


def create_workspace(workspace_name, capacity_name: str = "none", upns: list = None):
    print(f"::group::Creating workspace: {workspace_name}")

    command = f"create /{workspace_name}.Workspace"
    if capacity_name:
        command += f" -P capacityName={capacity_name}"

    run_fab_command(command, silently_continue=True)

    if upns:
        upns = [x for x in upns if x.strip()]
        for upn in upns:
            run_fab_command(f"acl set -f /{workspace_name}.Workspace -I {upn} -R admin")

    workspace_id = run_fab_command(
        f"get /{workspace_name}.Workspace -q id", capture_output=True
    )

    print(f"::endgroup::")
    return workspace_id


def create_connection(connection_name: str = None, parameters: dict = None, upns: list = None):
    print(f"::group::Creating connection {connection_name}")

    param_str = (
        f"-P {','.join(f'{key}={value}' for key, value in parameters.items())}"
        if parameters else ""
    )

    run_fab_command(
        f"create .connections/{connection_name}.Connection {param_str}",
        silently_continue=True,
    )

    connection_id = run_fab_command(
        f"get .connections/{connection_name}.Connection -q id", capture_output=True
    )

    if upns:
        upns = [x for x in upns if x.strip()]
        for upn in upns:
            run_fab_command(
                f"acl set -f .connections/{connection_name}.Connection -I {upn} -R admin"
            )

    print(f"::endgroup::")
    return connection_id


def create_item(workspace_name: str = None, item_type: str = None, item_name: str = None, parameters: dict = None):
    print(f"::group::Creating item {workspace_name}/{item_name}.{item_type}")

    param_str = (
        f"-P {','.join(f'{key}={value}' for key, value in parameters.items())}"
        if parameters else ""
    )

    run_fab_command(
        f"create /{workspace_name}.workspace/{item_name}.{item_type} {param_str}",
        silently_continue=True,
    )

    item_id = run_fab_command(
        f"get /{workspace_name}.workspace/{item_name}.{item_type} -q id",
        capture_output=True,
    )

    print(f"::endgroup::")
    return item_id


def deploy_item(
    src_path,
    workspace_name,
    item_type: str = None,
    item_name: str = None,
    find_and_replace: dict = None,
    what_if: bool = False,
    func_after_staging=None,
):
    print(f"::group::Deploying {src_path}")

    staging_path = copy_to_staging(src_path)

    if func_after_staging:
        func_after_staging(staging_path)

    platform_file = os.path.join(staging_path, ".platform")
    if os.path.exists(platform_file):
        with open(platform_file, "r") as file:
            platform_data = json.load(file)

        if item_name is None:
            item_name = platform_data["metadata"]["displayName"]

        if item_type is None:
            item_type = platform_data["metadata"]["type"]

    if find_and_replace:
        for root, _, files in os.walk(staging_path):
            for file in files:
                file_path = os.path.join(root, file)

                with open(file_path, "r") as file_reader:
                    text = file_reader.read()

                for (file_filter, find_pattern), replacement in find_and_replace.items():
                    if re.search(file_filter, file_path):
                        text, count_subs = re.subn(find_pattern, replacement, text)
                        if count_subs > 0:
                            print(f"Replaced {count_subs} occurrence(s) in {file_path}")
                            with open(file_path, "w") as file_writer:
                                file_writer.write(text)

    if not what_if:
        run_fab_command(
            f"import -f /{workspace_name}.workspace/{item_name}.{item_type} -i {staging_path}"
        )

        item_id = run_fab_command(
            f"get /{workspace_name}.workspace/{item_name}.{item_type} -q id",
            capture_output=True,
        )
        return item_id

    print(f"::endgroup::")


def copy_to_staging(path):
    """
    Copies the contents of the given directory into a clean `_stg/<foldername>` directory.
    """

    current_folder = os.path.dirname(__file__) if '__file__' in globals() else os.getcwd()
    path_staging = os.path.join(current_folder, "_stg", os.path.basename(path))

    if os.path.exists(path_staging):
        shutil.rmtree(path_staging)

    os.makedirs(path_staging)

    shutil.copytree(
        path, path_staging, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.abf")
    )

    return path_staging
