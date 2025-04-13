// Micro-interactions and enhanced animations for TaskSpree
// This file provides micro-interactions, confetti celebrations, and particle effects

// ========= Confetti Celebration for Task Completion =========
class ConfettiCelebration {
    constructor() {
        this.confettiColors = [
            '#FF577F', '#FF884B', '#FFBD9B', '#8D72E1', '#8D9EFF', 
            '#6C4AB6', '#8D72E1', '#B9E0FF', '#8D9EFF', '#6C4AB6'
        ];
        this.confettiAnimationId = null;
        this.particles = [];
        this.particleCount = 150;
        this.gravity = 0.8;
        this.terminalVelocity = 8;
        this.drag = 0.075;
        this.canvas = null;
        this.ctx = null;
    }

    // Initialize the canvas for confetti
    initCanvas() {
        // Create canvas if it doesn't exist
        if (!this.canvas) {
            this.canvas = document.createElement('canvas');
            this.canvas.id = 'confetti-canvas';
            this.canvas.style.position = 'fixed';
            this.canvas.style.top = '0';
            this.canvas.style.left = '0';
            this.canvas.style.width = '100%';
            this.canvas.style.height = '100%';
            this.canvas.style.pointerEvents = 'none';
            this.canvas.style.zIndex = '9999';
            document.body.appendChild(this.canvas);
            this.ctx = this.canvas.getContext('2d');
        }

        // Ensure canvas is properly sized
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }

    // Resize canvas to match window size
    resizeCanvas() {
        if (this.canvas) {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
        }
    }

    // Create confetti particles
    createConfettiParticles() {
        this.particles = [];
        for (let i = 0; i < this.particleCount; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height - this.canvas.height,
                rotation: Math.random() * 360,
                color: this.confettiColors[Math.floor(Math.random() * this.confettiColors.length)],
                size: 5 + Math.random() * 15,
                velocity: {
                    x: Math.random() * 6 - 3,
                    y: Math.random() * 3 + 2
                },
                rotationSpeed: (Math.random() - 0.5) * 2,
                shape: Math.random() > 0.5 ? 'circle' : 'rect'
            });
        }
    }

    // Update confetti particles
    updateConfetti() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        let remainingParticles = false;

        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];
            this.ctx.save();

            // Apply gravity and drag
            p.velocity.y = Math.min(p.velocity.y + this.gravity, this.terminalVelocity);
            p.velocity.y *= (1 - this.drag);
            p.velocity.x *= (1 - this.drag);

            // Update position
            p.x += p.velocity.x;
            p.y += p.velocity.y;
            p.rotation += p.rotationSpeed;

            // Render particle
            this.ctx.translate(p.x, p.y);
            this.ctx.rotate(p.rotation * Math.PI / 180);
            this.ctx.fillStyle = p.color;

            if (p.shape === 'circle') {
                this.ctx.beginPath();
                this.ctx.arc(0, 0, p.size / 2, 0, 2 * Math.PI);
                this.ctx.fill();
            } else {
                this.ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
            }
            
            this.ctx.restore();

            // Check if at least one particle is still visible
            if (p.y < this.canvas.height + p.size) {
                remainingParticles = true;
            }
        }

        // Continue animation if particles remain
        if (remainingParticles) {
            this.confettiAnimationId = requestAnimationFrame(() => this.updateConfetti());
        } else {
            this.stopConfetti();
        }
    }

    // Start the confetti celebration
    startConfetti() {
        this.initCanvas();
        this.createConfettiParticles();
        if (this.confettiAnimationId) {
            cancelAnimationFrame(this.confettiAnimationId);
        }
        this.confettiAnimationId = requestAnimationFrame(() => this.updateConfetti());
        
        // Play celebration sound
        const completeSound = document.getElementById('completeSound') || new Audio('/static/sounds/complete.mp3');
        completeSound.volume = 0.4;
        completeSound.currentTime = 0;
        completeSound.play().catch(() => {});
    }

    // Stop the confetti celebration
    stopConfetti() {
        if (this.confettiAnimationId) {
            cancelAnimationFrame(this.confettiAnimationId);
            this.confettiAnimationId = null;
        }
        
        if (this.canvas) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }
}

// ========= Particle Background System =========
class ParticleBackgroundSystem {
    constructor() {
        this.particles = [];
        this.maxParticles = 50; // Reduced for performance
        // Updated to purple and silver colors with reduced opacity
        this.colors = [
            'rgba(138, 43, 226, 0.15)',  // Purple
            'rgba(147, 112, 219, 0.15)', // Medium Purple
            'rgba(138, 43, 226, 0.1)',   // Lighter Purple
            'rgba(192, 192, 192, 0.12)', // Silver
            'rgba(169, 169, 169, 0.1)'   // Dark Silver
        ];
        this.canvas = null;
        this.ctx = null;
        this.animationId = null;
        this.mousePosition = { x: 0, y: 0 };
        this.mouseRadius = 100;
    }

    // Initialize the canvas for particles
    initCanvas() {
        // Only create if it doesn't exist
        if (!this.canvas) {
            this.canvas = document.createElement('canvas');
            this.canvas.id = 'particle-canvas';
            this.canvas.style.position = 'fixed';
            this.canvas.style.top = '0';
            this.canvas.style.left = '0';
            this.canvas.style.width = '100%';
            this.canvas.style.height = '100%';
            this.canvas.style.pointerEvents = 'none';
            this.canvas.style.zIndex = '0'; // Just above background, below content
            
            // Insert right after the background element
            const bgElement = document.querySelector('.particles') || document.body.firstChild;
            document.body.insertBefore(this.canvas, bgElement ? bgElement.nextSibling : document.body.firstChild);
            
            this.ctx = this.canvas.getContext('2d');
        }

        // Set canvas size
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());

        // Track mouse movement
        document.addEventListener('mousemove', (e) => {
            this.mousePosition.x = e.clientX;
            this.mousePosition.y = e.clientY;
        });
    }

    // Resize canvas to window size
    resizeCanvas() {
        if (this.canvas) {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
            // Recreate particles when canvas is resized
            this.createParticles();
        }
    }

    // Create initial particles
    createParticles() {
        this.particles = [];
        for (let i = 0; i < this.maxParticles; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                radius: Math.random() * 5 + 2,
                color: this.colors[Math.floor(Math.random() * this.colors.length)],
                velocity: {
                    x: Math.random() * 0.5 - 0.25,
                    y: Math.random() * 0.5 - 0.25
                },
                opacity: Math.random() * 0.5 + 0.3,
                originalRadius: Math.random() * 5 + 2
            });
        }
    }

    // Update and draw particles
    updateParticles() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];
            
            // Update position
            p.x += p.velocity.x;
            p.y += p.velocity.y;
            
            // Wrap around edges
            if (p.x < 0) p.x = this.canvas.width;
            if (p.x > this.canvas.width) p.x = 0;
            if (p.y < 0) p.y = this.canvas.height;
            if (p.y > this.canvas.height) p.y = 0;
            
            // Calculate distance from mouse
            const dx = this.mousePosition.x - p.x;
            const dy = this.mousePosition.y - p.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            // Interactive effect with mouse
            if (distance < this.mouseRadius) {
                const angle = Math.atan2(dy, dx);
                const force = (this.mouseRadius - distance) / this.mouseRadius;
                
                // Push particle away from mouse
                p.velocity.x -= Math.cos(angle) * force * 0.02;
                p.velocity.y -= Math.sin(angle) * force * 0.02;
                
                // Temporarily increase size
                p.radius = p.originalRadius * (1 + force);
            } else {
                // Gradually return to original size
                p.radius += (p.originalRadius - p.radius) * 0.1;
            }
            
            // Draw particle
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            this.ctx.fillStyle = p.color.replace(')', `, ${p.opacity})`);
            this.ctx.fill();
            
            // Connect nearby particles with lines
            for (let j = i + 1; j < this.particles.length; j++) {
                const p2 = this.particles[j];
                const dx = p.x - p2.x;
                const dy = p.y - p2.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < 100) {
                    this.ctx.beginPath();
                    this.ctx.strokeStyle = `rgba(138, 43, 226, ${0.1 * (1 - distance / 100)})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.moveTo(p.x, p.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.stroke();
                }
            }
        }
        
        this.animationId = requestAnimationFrame(() => this.updateParticles());
    }

    // Start the particle animation
    startParticles() {
        this.initCanvas();
        this.createParticles();
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        this.animationId = requestAnimationFrame(() => this.updateParticles());
    }

    // Stop the particle animation
    stopParticles() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        
        if (this.canvas && this.ctx) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }
}

// ========= Micro-Interactions System =========
class MicroInteractions {
    constructor() {
        this.interactiveSelectors = [
            '.btn', 
            '.nav-link', 
            '.task-item', 
            '.rank-badge', 
            '.form-control',
            '.dropdown-item'
        ];
    }

    // Initialize all micro-interactions
    init() {
        this.setupButtonInteractions();
        this.setupInputInteractions();
        this.setupTaskItemInteractions();
        this.setupNavItemInteractions();
        this.setupRankBadgeInteractions();
    }

    // Button interaction effects
    setupButtonInteractions() {
        document.querySelectorAll('.btn').forEach(button => {
            // Add ripple effect to all buttons
            button.addEventListener('click', (e) => {
                this.createRippleEffect(e, button);
            });
            
            // Add magnetic hover effect
            button.addEventListener('mousemove', (e) => {
                this.createMagneticEffect(e, button);
            });
            
            button.addEventListener('mouseleave', () => {
                gsap.to(button, {
                    x: 0,
                    y: 0,
                    duration: 0.5,
                    ease: 'elastic.out(1, 0.3)'
                });
            });
        });
    }

    // Input field interactions
    setupInputInteractions() {
        document.querySelectorAll('.form-control').forEach(input => {
            // Add focus animation
            input.addEventListener('focus', () => {
                gsap.to(input, {
                    scale: 1.02,
                    boxShadow: '0 0 15px rgba(138, 43, 226, 0.3)',
                    duration: 0.3,
                    ease: 'power2.out'
                });
            });
            
            input.addEventListener('blur', () => {
                gsap.to(input, {
                    scale: 1,
                    boxShadow: '0 0 0px rgba(138, 43, 226, 0)',
                    duration: 0.3,
                    ease: 'power2.out'
                });
            });
        });
    }

    // Task item interactions
    setupTaskItemInteractions() {
        document.querySelectorAll('.task-item').forEach(taskItem => {
            // Add tilt effect on hover
            taskItem.addEventListener('mousemove', (e) => {
                const bounds = taskItem.getBoundingClientRect();
                const mouseX = e.clientX - bounds.left;
                const mouseY = e.clientY - bounds.top;
                const centerX = bounds.width / 2;
                const centerY = bounds.height / 2;
                
                const rotateX = (mouseY - centerY) / 25;
                const rotateY = (centerX - mouseX) / 25;
                
                gsap.to(taskItem, {
                    rotationX: rotateX,
                    rotationY: rotateY,
                    transformPerspective: 1000,
                    ease: 'power2.out',
                    duration: 0.3
                });
            });
            
            taskItem.addEventListener('mouseleave', () => {
                gsap.to(taskItem, {
                    rotationX: 0,
                    rotationY: 0,
                    duration: 0.3,
                    ease: 'power2.out'
                });
            });
        });
    }

    // Navigation item interactions
    setupNavItemInteractions() {
        document.querySelectorAll('.nav-link').forEach(navLink => {
            navLink.addEventListener('mouseenter', () => {
                gsap.to(navLink, {
                    y: -3,
                    duration: 0.3,
                    ease: 'power2.out'
                });
            });
            
            navLink.addEventListener('mouseleave', () => {
                gsap.to(navLink, {
                    y: 0,
                    duration: 0.3,
                    ease: 'power2.out'
                });
            });
        });
    }

    // Rank badge interactions
    setupRankBadgeInteractions() {
        document.querySelectorAll('.rank-badge').forEach(badge => {
            badge.addEventListener('mouseenter', () => {
                gsap.to(badge, {
                    scale: 1.1,
                    rotation: 5,
                    duration: 0.3,
                    ease: 'back.out(1.7)'
                });
            });
            
            badge.addEventListener('mouseleave', () => {
                gsap.to(badge, {
                    scale: 1,
                    rotation: 0,
                    duration: 0.3,
                    ease: 'power2.out'
                });
            });
        });
    }

    // Create ripple effect
    createRippleEffect(event, element) {
        const ripple = document.createElement('span');
        ripple.className = 'micro-ripple';
        element.appendChild(ripple);
        
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        
        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
        ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
        
        ripple.classList.add('active');
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    // Create magnetic effect
    createMagneticEffect(event, element) {
        const rect = element.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        const distanceX = event.clientX - centerX;
        const distanceY = event.clientY - centerY;
        
        // Decrease the divisor to make the effect stronger
        const moveX = distanceX / 10;
        const moveY = distanceY / 10;
        
        gsap.to(element, {
            x: moveX,
            y: moveY,
            duration: 0.3,
            ease: 'power2.out'
        });
    }
}

// ========= Initialize Systems on DOM Load =========
document.addEventListener('DOMContentLoaded', function() {
    // Initialize particle background system
    const particleSystem = new ParticleBackgroundSystem();
    particleSystem.startParticles();
    
    // Initialize micro-interactions
    // Check if GSAP is available, and load it if not
    if (typeof gsap === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.11.4/gsap.min.js';
        script.onload = function() {
            const microInteractions = new MicroInteractions();
            microInteractions.init();
        };
        document.head.appendChild(script);
    } else {
        const microInteractions = new MicroInteractions();
        microInteractions.init();
    }
    
    // Create global instances
    window.confettiCelebration = new ConfettiCelebration();
    
    // Add CSS for micro-interactions
    const style = document.createElement('style');
    style.textContent = `
        .micro-ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: scale(0);
            pointer-events: none;
            z-index: 10;
        }
        
        .micro-ripple.active {
            animation: ripple-effect 0.6s linear;
        }
        
        @keyframes ripple-effect {
            0% { transform: scale(0); opacity: 0.3; }
            100% { transform: scale(2); opacity: 0; }
        }
        
        /* Improve button interactions */
        .btn {
            overflow: hidden;
            transform-style: preserve-3d;
            backface-visibility: hidden;
        }
        
        /* Add more vibrant hover states for interactive elements */
        .hover-glow:hover {
            filter: brightness(1.2) drop-shadow(0 0 5px rgba(138, 43, 226, 0.5));
        }
    `;
    document.head.appendChild(style);
    
    // Override the task completion function to add confetti
    const originalHandleTaskComplete = window.handleTaskComplete;
    if (originalHandleTaskComplete) {
        window.handleTaskComplete = async function(taskId) {
            await originalHandleTaskComplete(taskId);
            // Trigger confetti celebration after task is completed
            if (window.confettiCelebration) {
                window.confettiCelebration.startConfetti();
            }
        };
    }
});