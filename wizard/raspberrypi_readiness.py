import os
import subprocess

def run_command(command, description):
    """Run a shell command and display its progress."""
    print(f"\nRunning: {description}")
    process = subprocess.run(command, shell=True)
    if process.returncode == 0:
        print(f"[SUCCESS] {description}")
    else:
        print(f"[ERROR] {description}")

def main():
    print("\nRASPBERRYPI 5 READINESS (STAGE 1)\n")

    # Step 1: Update and Upgrade System
    run_command("sudo apt update -y && sudo apt upgrade -y", "Updating and upgrading the system")

    # Step 2: Remove Unnecessary Packages and Clean Up
    run_command("sudo apt autoremove -y && sudo apt autoclean -y", "Removing unnecessary packages and cleaning up")

    # Step 3: Re-run Updates to Sync Repositories
    run_command("sudo apt update -y && sudo apt upgrade -y", "Re-running updates to sync repositories")

    # Step 4: Install Python3 and pip
    run_command("sudo apt install -y python3 python3-venv python3-pip", "Installing Python3, venv, and pip")

    # Step 5: Install iotop for Monitoring
    run_command("sudo apt install -y iotop", "Installing iotop for monitoring")

    # Step 6: Install logrotate for Log Management
    run_command("sudo apt install logrotate", "Installing logrotate to manage log files")

    # Step 7: Final Update and Upgrade Cycle
    run_command("sudo apt update -y && sudo apt upgrade -y", "Final update and upgrade cycle")

    # Step 8: Final Cleanup
    run_command("sudo apt autoremove -y && sudo apt autoclean -y", "Final cleanup of unnecessary packages")

    print("\n[INFO] RaspberryPi 5 is now ready and optimized!")

if __name__ == "__main__":
    main()
