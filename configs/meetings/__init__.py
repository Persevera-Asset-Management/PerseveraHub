"""
Meeting configurations package
"""

# Import meeting configurations dynamically based on meeting name
def get_meeting_config(meeting_name):
    """
    Dynamically imports and returns the configuration for a specific meeting.
    
    Parameters:
    -----------
    meeting_name : str
        Name of the meeting, corresponding to a module in this package
        
    Returns:
    --------
    module
        The imported meeting configuration module
    
    Raises:
    -------
    ImportError
        If the specified meeting config doesn't exist
    """
    try:
        module_name = f"configs.meetings.{meeting_name}"
        meeting_module = __import__(module_name, fromlist=["*"])
        return meeting_module
    except ImportError:
        raise ImportError(f"Meeting configuration for '{meeting_name}' not found. Make sure the file exists in the configs/meetings directory.") 