import os
import json

# Function to convert the JSON data to Mermaid syntax for a flowchart
def convert_to_mermaid_syntax(data):
    diagram = 'graph TD\n'  # Mermaid syntax for flowchart

    # Loop through the data to create nodes and links
    for file, details in data.items():
        dependencies = details.get('dependencies', {})
        # Loop through the dependencies of each file
        for dep, dep_details in dependencies.items():
            functions = dep_details.get('functions', [])
            # Create edges between files, and show the functions being called
            diagram += f"{file.replace('\\', '\\\\')} -->|{', '.join(functions)}| {dep.replace('\\', '\\\\')}\n"
    
    return diagram

# Function to generate HTML content with the Mermaid diagram
def generate_html(file_name, mermaid_syntax):
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dependency Diagram</title>
        <style>
            #mySvgId {{
                height: 90%;
                width: 100%;
            }}
        </style>
    </head>
    <body>
        <div id="classDiv"></div>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.js"></script>
        <script src="https://bumbu.me/svg-pan-zoom/dist/svg-pan-zoom.min.js"></script>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.js';
            mermaid.initialize({
                startOnLoad: false,
                maxTextSize: 90000
            });

            const drawDiagram = async function () {{
                const element = document.querySelector('#classDiv');
                const diagramSyntax = `{mermaid_syntax}`;

                const {{ svg }} = await mermaid.render('mySvgId', diagramSyntax);

                element.innerHTML = svg.replace(/max-width:\\d+px;/i, '');

                let doPan = false;
                let mousepos;
                const eventsHandler = {{
                    mouseDownHandler: function (ev) {{
                        if (ev.target.className.baseVal === "class") {{
                            doPan = true;
                            mousepos = {{ x: ev.clientX, y: ev.clientY }};
                        }}
                    }},
                    mouseMoveHandler: function (ev) {{
                        if (doPan) {{
                            panZoom.panBy({{ x: ev.clientX - mousepos.x, y: ev.clientY - mousepos.y }});
                            mousepos = {{ x: ev.clientX, y: ev.clientY }};
                            window.getSelection().removeAllRanges();  // Prevent text selection during pan
                        }}
                    }},
                    mouseUpHandler: function () {{
                        doPan = false;
                    }},
                    init: function (options) {{
                        options.svgElement.addEventListener('mousedown', this.mouseDownHandler, false);
                        options.svgElement.addEventListener('mousemove', this.mouseMoveHandler, false);
                        options.svgElement.addEventListener('mouseup', this.mouseUpHandler, false);
                    }},
                    destroy: function (options) {{
                        options.svgElement.removeEventListener('mousedown', this.mouseDownHandler, false);
                        options.svgElement.removeEventListener('mousemove', this.mouseMoveHandler, false);
                        options.svgElement.removeEventListener('mouseup', this.mouseUpHandler, false);
                    }}
                }};

                const panZoom = svgPanZoom('#mySvgId', {{
                    zoomEnabled: true,
                    controlIconsEnabled: true,
                    fit: 1,
                    center: 1,
                    customEventsHandler: eventsHandler
                }});
            }};

            await drawDiagram();
        </script>
    </body>
    </html>
    """
    # Write the HTML file to disk
    with open(file_name, 'w') as file:
        file.write(html_template)

# Directory containing your JSON files
json_folder = 'path_to_your_json_folder'

# Iterate over each JSON file in the directory
for json_filename in os.listdir(json_folder):
    if json_filename.endswith('.json'):
        json_file_path = os.path.join(json_folder, json_filename)
        
        # Read the JSON file
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        # Convert JSON data to Mermaid syntax
        mermaid_syntax = convert_to_mermaid_syntax(data)
        
        # Create an HTML file name from the JSON file name
        html_filename = os.path.splitext(json_filename)[0] + '.html'
        html_file_path = os.path.join(json_folder, html_filename)
        
        # Generate HTML file
        generate_html(html_file_path, mermaid_syntax)
        print(f"Generated HTML file: {html_file_path}")
