document.addEventListener('DOMContentLoaded', () => {
    const projectSelect = document.getElementById('project-select');
    const resetBtn = document.getElementById('reset-layout');
    let cy;
    let registryData = [];

    // Initialize Cytoscape Dagre layout
    cytoscape.use(cytoscapeDagre);

    // Fetch the registry
    fetch('registry.json')
        .then(response => response.json())
        .then(data => {
            registryData = data;
            projectSelect.innerHTML = '<option value="">-- Select Project --</option>';
            data.forEach((project, index) => {
                const option = document.createElement('option');
                option.value = index;
                option.textContent = `${project.name} (${project.language})`;
                projectSelect.appendChild(option);
            });

            // Automatically load the first project if available
            if(data.length > 0) {
                projectSelect.value = 0;
                loadProject(data[0]);
            }
        })
        .catch(err => {
            console.error('Error loading registry:', err);
            projectSelect.innerHTML = '<option value="">Error loading registry</option>';
        });

    projectSelect.addEventListener('change', (e) => {
        const index = e.target.value;
        if (index !== "") {
            loadProject(registryData[index]);
        } else {
            if (cy) cy.destroy();
        }
    });

    resetBtn.addEventListener('click', () => {
        if (cy) {
            cy.layout({ name: 'dagre', rankDir: 'LR', spacingFactor: 1.5 }).run();
        }
    });

    function loadProject(project) {
        // The GitHub Action copies the sample directory INTO the viewer directory.
        // So from index.html (at viewer/index.html), the path is simply the project path (e.g. "./sample/graph.json")
        // Since project.path is "./sample", we can use it directly if we ensure it starts with './'
        let basePath = project.path;
        if (!basePath.startsWith('./')) {
            basePath = './' + basePath;
        }
        const graphUrl = `${basePath}/${project.graph_file}`;

        fetch(graphUrl)
            .then(res => res.json())
            .then(graphData => {
                renderGraph(graphData);
            })
            .catch(err => {
                console.error(`Error loading graph for ${project.name}:`, err);
                alert(`Could not load graph data for ${project.name}. Check console for details.`);
            });
    }

    function renderGraph(graphData) {
        if (cy) cy.destroy();

        // Convert networkx node-link JSON to Cytoscape elements
        const elements = [];

        if (graphData.nodes) {
            graphData.nodes.forEach(node => {
                elements.push({
                    data: {
                        id: node.id,
                        label: node.label || node.id,
                        type: node.type || 'unknown'
                    }
                });
            });
        }

        if (graphData.edges) {
            graphData.edges.forEach((edge, index) => {
                elements.push({
                    data: {
                        id: `e${index}`,
                        source: edge.source,
                        target: edge.target,
                        type: edge.type || 'unknown'
                    }
                });
            });
        }

        cy = cytoscape({
            container: document.getElementById('cy'),
            elements: elements,
            style: [
                // Node styles
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'color': '#fff',
                        'text-outline-width': 2,
                        'text-outline-color': '#555',
                        'font-size': '12px',
                        'width': 'label',
                        'height': 'label',
                        'padding': '10px',
                        'shape': 'round-rectangle'
                    }
                },
                {
                    selector: 'node[type = "file"]',
                    style: {
                        'background-color': '#3498db',
                        'text-outline-color': '#2980b9'
                    }
                },
                {
                    selector: 'node[type = "class"]',
                    style: {
                        'background-color': '#e74c3c',
                        'text-outline-color': '#c0392b'
                    }
                },
                {
                    selector: 'node[type = "method"]',
                    style: {
                        'background-color': '#2ecc71',
                        'text-outline-color': '#27ae60',
                        'shape': 'ellipse',
                        'padding': '5px'
                    }
                },
                {
                    selector: 'node[type = "function"]',
                    style: {
                        'background-color': '#1abc9c',
                        'text-outline-color': '#16a085',
                        'shape': 'ellipse',
                        'padding': '5px'
                    }
                },
                // Edge styles
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'curve-style': 'bezier',
                        'target-arrow-shape': 'triangle',
                        'opacity': 0.8
                    }
                },
                {
                    selector: 'edge[type = "contains"]',
                    style: {
                        'line-color': '#95a5a6',
                        'target-arrow-color': '#95a5a6'
                    }
                },
                {
                    selector: 'edge[type = "imports"]',
                    style: {
                        'line-color': '#f39c12',
                        'target-arrow-color': '#f39c12',
                        'line-style': 'dashed'
                    }
                },
                {
                    selector: 'edge[type = "inherits"]',
                    style: {
                        'line-color': '#9b59b6',
                        'target-arrow-color': '#9b59b6',
                        'target-arrow-shape': 'triangle-tee',
                        'width': 3
                    }
                },
                {
                    selector: 'edge[type = "calls"]',
                    style: {
                        'line-color': '#e67e22',
                        'target-arrow-color': '#e67e22',
                        'curve-style': 'unbundled-bezier',
                        'control-point-distances': 20,
                        'control-point-weights': 0.5
                    }
                }
            ],
            layout: {
                name: 'dagre',
                rankDir: 'LR',
                spacingFactor: 1.5
            },
            wheelSensitivity: 0.2
        });

        // Add tooltips or basic interactions
        cy.on('tap', 'node', function(evt){
            var node = evt.target;
            console.log('Tapped ' + node.data('id'));
        });
    }
});
