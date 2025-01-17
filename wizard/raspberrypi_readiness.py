import subprocess
import sys

def run_command(command, description=None, exit_on_failure=False):
    """
    Run a shell command and optionally exit if the command fails.
    
    :param command: Command to be executed.
    :param description: Text to display before running the command (optional).
    :param exit_on_failure: If True, the script will exit on the command's failure.
    :return: None
    """
    desc = description or command
    print(f"\n[+] Running: {desc}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Output for debugging/logging
        if result.stdout.strip():
            print("    Output:")
            print(result.stdout.strip())
        print(f"[SUCCESS] {desc}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or str(e)
        print(f"[ERROR] {desc}\n    Reason: {error_msg}")
        if exit_on_failure:
            sys.exit(1)


def main():
    print("\n========== RASPBERRYPI 5 READINESS (STAGE 1) ==========\n")

    # Step 1: Update and Upgrade System (critical)
    run_command(
        "sudo apt update -y && sudo apt upgrade -y", 
        "Updating and upgrading the system", 
        exit_on_failure=True
    )

    # Step 2: Remove Unnecessary Packages and Clean Up
    run_command(
        "sudo apt autoremove -y && sudo apt autoclean -y", 
        "Removing unnecessary packages and cleaning up"
    )

    # Step 3: Re-run Updates to Sync Repositories
    run_command(
        "sudo apt update -y && sudo apt upgrade -y", 
        "Re-running updates to sync repositories"
    )

    # Step 4: Install Python3 and pip
    run_command(
        "sudo apt install -y python3 python3-venv python3-pip", 
        "Installing Python3, venv, and pip"
    )

    # Step 5: Install iotop for Monitoring
    run_command(
        "sudo apt install -y iotop", 
        "Installing iotop for monitoring"
    )

    # Step 6: Install logrotate for Log Management
    run_command(
        "sudo apt install -y logrotate", 
        "Installing logrotate to manage log files"
    )

    # Step 7: Final Update and Upgrade Cycle
    run_command(
        "sudo apt update -y && sudo apt upgrade -y", 
        "Final update and upgrade cycle"
    )

    # Step 8: Final Cleanup
    run_command(
        "sudo apt autoremove -y && sudo apt autoclean -y", 
        "Final cleanup of unnecessary packages"
    )

    print("\n[INFO] RaspberryPi 5 is now ready and optimized!")

if __name__ == "__main__":
    main()
