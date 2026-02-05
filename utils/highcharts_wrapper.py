import streamlit.components.v1 as components
import json

def render_highcharts_with_fullscreen(chart_options, key=None, height=None):
    """
    Renders a Highcharts chart with double-click fullscreen support.
    
    Parameters:
    -----------
    chart_options : dict
        Highcharts configuration options
    key : str, optional
        Unique key for the component
    height : int, optional
        Height of the chart container in pixels
    """
    # Convert chart options to JSON, handling height
    chart_height = height or chart_options.get("chart", {}).get("height", 400)
    
    # Convert options to JSON string
    options_json = json.dumps(chart_options)
    
    # HTML template with Highcharts and double-click fullscreen
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <script src="https://code.highcharts.com/modules/exporting.js"></script>
        <script src="https://code.highcharts.com/modules/export-data.js"></script>
        <script src="https://code.highcharts.com/modules/accessibility.js"></script>
        <script src="https://code.highcharts.com/modules/full-screen.js"></script>
        <script src="https://code.highcharts.com/modules/heatmap.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
            }}
            #container {{
                width: 100%;
                height: {chart_height}px;
            }}
        </style>
    </head>
    <body>
        <div id="container"></div>
        <script>
            // Parse the chart options
            var chartOptions = {options_json};
            
            // Create the chart
            var chart = Highcharts.chart('container', chartOptions);
            
            // Add double-click event listener for fullscreen toggle
            chart.container.addEventListener('dblclick', function() {{
                chart.fullscreen.toggle();
            }});
        </script>
    </body>
    </html>
    """
    
    # Render the component
    components.html(html_template, height=chart_height + 50, scrolling=False)
