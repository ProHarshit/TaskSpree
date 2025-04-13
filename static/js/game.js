// Simple multiplayer game implementation
class GameEngine {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas?.getContext('2d');
        this.players = new Map();
        this.localPlayer = null;
        this.gameLoop = null;
        this.keys = new Set();
        
        if (this.canvas) {
            this.setupGame();
        }
    }

    setupGame() {
        // Set canvas size
        this.canvas.width = 800;
        this.canvas.height = 600;

        // Create local player
        this.localPlayer = {
            x: Math.random() * (this.canvas.width - 30),
            y: Math.random() * (this.canvas.height - 30),
            color: `hsl(${Math.random() * 360}, 70%, 50%)`,
            size: 30,
            speed: 5,
            score: 0
        };

        // Setup input handlers
        window.addEventListener('keydown', (e) => this.keys.add(e.key));
        window.addEventListener('keyup', (e) => this.keys.delete(e.key));

        // Start game loop
        this.gameLoop = setInterval(() => {
            this.update();
            this.draw();
        }, 1000 / 60);
    }

    update() {
        // Update local player position based on input
        if (this.keys.has('ArrowUp')) this.localPlayer.y -= this.localPlayer.speed;
        if (this.keys.has('ArrowDown')) this.localPlayer.y += this.localPlayer.speed;
        if (this.keys.has('ArrowLeft')) this.localPlayer.x -= this.localPlayer.speed;
        if (this.keys.has('ArrowRight')) this.localPlayer.x += this.localPlayer.speed;

        // Keep player in bounds
        this.localPlayer.x = Math.max(0, Math.min(this.canvas.width - this.localPlayer.size, this.localPlayer.x));
        this.localPlayer.y = Math.max(0, Math.min(this.canvas.height - this.localPlayer.size, this.localPlayer.y));

        // Collect points
        this.checkCollisions();
    }

    draw() {
        // Clear canvas
        this.ctx.fillStyle = '#2c2f33';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw grid
        this.ctx.strokeStyle = '#99aab5';
        this.ctx.lineWidth = 1;
        for (let i = 0; i < this.canvas.width; i += 50) {
            this.ctx.beginPath();
            this.ctx.moveTo(i, 0);
            this.ctx.lineTo(i, this.canvas.height);
            this.ctx.stroke();
        }
        for (let i = 0; i < this.canvas.height; i += 50) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, i);
            this.ctx.lineTo(this.canvas.width, i);
            this.ctx.stroke();
        }

        // Draw local player
        this.drawPlayer(this.localPlayer);

        // Draw other players
        this.players.forEach(player => this.drawPlayer(player));

        // Draw score
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = '20px Arial';
        this.ctx.fillText(`Score: ${this.localPlayer.score}`, 10, 30);
    }

    drawPlayer(player) {
        this.ctx.fillStyle = player.color;
        this.ctx.beginPath();
        this.ctx.arc(player.x + player.size/2, player.y + player.size/2, 
                    player.size/2, 0, Math.PI * 2);
        this.ctx.fill();
    }

    checkCollisions() {
        // Check collisions with other players
        this.players.forEach((player, id) => {
            const dx = this.localPlayer.x - player.x;
            const dy = this.localPlayer.y - player.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < this.localPlayer.size) {
                // Handle collision
                if (this.localPlayer.size > player.size) {
                    this.localPlayer.score += 10;
                    this.players.delete(id);
                }
            }
        });
    }

    cleanup() {
        if (this.gameLoop) {
            clearInterval(this.gameLoop);
        }
        this.keys.clear();
    }
}

// Initialize game when document is loaded
document.addEventListener('DOMContentLoaded', () => {
    const game = new GameEngine();

    // Cleanup on page unload
    window.addEventListener('unload', () => {
        game.cleanup();
    });
});
