#!/bin/bash

# Zenoo-RPC Production Deployment Script
# This script handles the complete deployment process for Zenoo-RPC

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOYMENT_DIR="${PROJECT_ROOT}/deployment"

# Default values
ENVIRONMENT="${ENVIRONMENT:-production}"
NAMESPACE="${NAMESPACE:-zenoo-production}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY="${REGISTRY:-}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_TESTS="${SKIP_TESTS:-false}"
SKIP_BUILD="${SKIP_BUILD:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Zenoo-RPC Production Deployment Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    build       Build Docker image
    test        Run tests
    deploy      Deploy to Kubernetes
    rollback    Rollback to previous version
    status      Check deployment status
    logs        Show application logs
    cleanup     Clean up old resources

Options:
    -e, --environment ENV    Target environment (default: production)
    -n, --namespace NS       Kubernetes namespace (default: zenoo-production)
    -t, --tag TAG           Docker image tag (default: latest)
    -r, --registry REG      Docker registry URL
    --dry-run               Show what would be done without executing
    --skip-tests            Skip running tests
    --skip-build            Skip building Docker image
    -h, --help              Show this help message

Examples:
    $0 build -t v1.0.0
    $0 test
    $0 deploy -e production -t v1.0.0
    $0 status
    $0 rollback
    $0 cleanup

Environment Variables:
    ENVIRONMENT             Target environment
    NAMESPACE               Kubernetes namespace
    IMAGE_TAG               Docker image tag
    REGISTRY                Docker registry URL
    DRY_RUN                 Dry run mode (true/false)
    SKIP_TESTS              Skip tests (true/false)
    SKIP_BUILD              Skip build (true/false)
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            --skip-build)
                SKIP_BUILD="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            build|test|deploy|rollback|status|logs|cleanup)
                COMMAND="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local required_tools=("docker" "kubectl" "python3")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check Kubernetes connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    local image_name="zenoo-rpc"
    local full_image_name="${image_name}:${IMAGE_TAG}"
    
    if [[ -n "$REGISTRY" ]]; then
        full_image_name="${REGISTRY}/${full_image_name}"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would build image: $full_image_name"
        return 0
    fi
    
    # Build image
    docker build \
        -f "${DEPLOYMENT_DIR}/Dockerfile.production" \
        -t "$full_image_name" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse HEAD)" \
        --build-arg VERSION="$IMAGE_TAG" \
        "$PROJECT_ROOT"
    
    # Push to registry if specified
    if [[ -n "$REGISTRY" ]]; then
        log_info "Pushing image to registry..."
        docker push "$full_image_name"
    fi
    
    log_success "Image built successfully: $full_image_name"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would run tests"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    # Run unit tests
    log_info "Running unit tests..."
    python -m pytest tests/ -v --tb=short --cov=src/zenoo_rpc --cov-report=term-missing
    
    # Run integration tests
    log_info "Running integration tests..."
    python -m pytest tests/test_integration_comprehensive.py -v
    
    # Run performance tests
    log_info "Running performance tests..."
    python -m pytest tests/test_performance_simple.py -v
    
    log_success "All tests passed"
}

# Deploy to Kubernetes
deploy_to_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Creating namespace: $NAMESPACE"
        if [[ "$DRY_RUN" != "true" ]]; then
            kubectl create namespace "$NAMESPACE"
        fi
    fi
    
    # Apply Kubernetes manifests
    local k8s_dir="${DEPLOYMENT_DIR}/k8s"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would apply Kubernetes manifests"
        kubectl apply --dry-run=client -f "$k8s_dir/" -n "$NAMESPACE"
        return 0
    fi
    
    # Apply manifests
    kubectl apply -f "$k8s_dir/" -n "$NAMESPACE"
    
    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    kubectl rollout status deployment/zenoo-rpc -n "$NAMESPACE" --timeout=300s
    
    # Verify deployment
    log_info "Verifying deployment..."
    kubectl get pods -n "$NAMESPACE" -l app=zenoo-rpc
    
    log_success "Deployment completed successfully"
}

# Check deployment status
check_status() {
    log_info "Checking deployment status..."
    
    # Check pods
    echo "Pods:"
    kubectl get pods -n "$NAMESPACE" -l app=zenoo-rpc
    
    # Check services
    echo -e "\nServices:"
    kubectl get services -n "$NAMESPACE" -l app=zenoo-rpc
    
    # Check ingress
    echo -e "\nIngress:"
    kubectl get ingress -n "$NAMESPACE" -l app=zenoo-rpc
    
    # Check HPA
    echo -e "\nHorizontal Pod Autoscaler:"
    kubectl get hpa -n "$NAMESPACE" -l app=zenoo-rpc
    
    # Run health check
    log_info "Running health check..."
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=zenoo-rpc -o jsonpath='{.items[0].metadata.name}')
    if [[ -n "$pod_name" ]]; then
        kubectl exec -n "$NAMESPACE" "$pod_name" -- python healthcheck.py
    else
        log_warning "No pods found for health check"
    fi
}

# Show logs
show_logs() {
    log_info "Showing application logs..."
    
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=zenoo-rpc -o jsonpath='{.items[0].metadata.name}')
    if [[ -n "$pod_name" ]]; then
        kubectl logs -n "$NAMESPACE" "$pod_name" --tail=100 -f
    else
        log_error "No pods found"
        exit 1
    fi
}

# Rollback deployment
rollback_deployment() {
    log_info "Rolling back deployment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rollback deployment"
        return 0
    fi
    
    kubectl rollout undo deployment/zenoo-rpc -n "$NAMESPACE"
    kubectl rollout status deployment/zenoo-rpc -n "$NAMESPACE" --timeout=300s
    
    log_success "Rollback completed successfully"
}

# Cleanup old resources
cleanup_resources() {
    log_info "Cleaning up old resources..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would cleanup old resources"
        return 0
    fi
    
    # Clean up old replica sets
    kubectl delete replicaset -n "$NAMESPACE" -l app=zenoo-rpc --field-selector='status.replicas=0'
    
    # Clean up old Docker images (if running locally)
    if command -v docker &> /dev/null; then
        docker image prune -f --filter "label=app=zenoo-rpc"
    fi
    
    log_success "Cleanup completed"
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"
    
    # Check if command is provided
    if [[ -z "${COMMAND:-}" ]]; then
        log_error "No command specified"
        show_help
        exit 1
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Execute command
    case "$COMMAND" in
        build)
            build_image
            ;;
        test)
            if [[ "$SKIP_TESTS" != "true" ]]; then
                run_tests
            else
                log_warning "Skipping tests"
            fi
            ;;
        deploy)
            if [[ "$SKIP_BUILD" != "true" ]]; then
                build_image
            fi
            if [[ "$SKIP_TESTS" != "true" ]]; then
                run_tests
            fi
            deploy_to_kubernetes
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        rollback)
            rollback_deployment
            ;;
        cleanup)
            cleanup_resources
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
