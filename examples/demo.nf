#!/usr/bin/env nextflow

/*
 * Demo pipeline for testing NF-Subway visualization
 * 
 * This pipeline simulates a typical bioinformatics workflow with
 * multiple processes and dependencies.
 */

nextflow.enable.dsl=2

params.input = "demo_data/*.txt"
params.outdir = "results"

process QUALITY_CHECK {
    publishDir "${params.outdir}/qc", mode: 'copy'
    
    input:
    tuple val(sample_id), path(input_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_qc.txt")
    
    script:
    """
    echo "Quality checking ${sample_id}..." > ${sample_id}_qc.txt
    sleep 2
    echo "Quality check passed!" >> ${sample_id}_qc.txt
    """
}

process TRIM_SEQUENCES {
    publishDir "${params.outdir}/trimmed", mode: 'copy'
    
    input:
    tuple val(sample_id), path(qc_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_trimmed.txt")
    
    script:
    """
    echo "Trimming ${sample_id}..." > ${sample_id}_trimmed.txt
    sleep 3
    echo "Trimming complete!" >> ${sample_id}_trimmed.txt
    """
}

process ALIGN_READS {
    publishDir "${params.outdir}/aligned", mode: 'copy'
    
    input:
    tuple val(sample_id), path(trimmed_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_aligned.txt")
    
    script:
    """
    echo "Aligning ${sample_id}..." > ${sample_id}_aligned.txt
    sleep 4
    echo "Alignment complete!" >> ${sample_id}_aligned.txt
    """
}

process COUNT_FEATURES {
    publishDir "${params.outdir}/counts", mode: 'copy'
    
    input:
    tuple val(sample_id), path(aligned_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_counts.txt")
    
    script:
    """
    echo "Counting features for ${sample_id}..." > ${sample_id}_counts.txt
    sleep 2
    echo "Counting complete!" >> ${sample_id}_counts.txt
    """
}

process GENERATE_REPORT {
    publishDir "${params.outdir}/reports", mode: 'copy'
    
    input:
    path(count_files)
    
    output:
    path "final_report.txt"
    
    script:
    """
    echo "Generating final report..." > final_report.txt
    echo "Processed ${count_files.size()} samples" >> final_report.txt
    sleep 2
    echo "Report complete!" >> final_report.txt
    """
}

workflow {
    // Create input channel with sample data
    input_ch = channel.of(
        ['sample1', file('demo_data/sample1.txt')],
        ['sample2', file('demo_data/sample2.txt')],
        ['sample3', file('demo_data/sample3.txt')]
    )
    
    // Run the pipeline
    qc_results = QUALITY_CHECK(input_ch)
    trimmed = TRIM_SEQUENCES(qc_results)
    aligned = ALIGN_READS(trimmed)
    counts = COUNT_FEATURES(aligned)
    
    // Generate final report
    all_counts = counts.map { sample_id, count_file -> count_file }.collect()
    GENERATE_REPORT(all_counts)
}

workflow.onComplete {
    println "Pipeline completed at: ${workflow.complete}"
    println "Execution status: ${workflow.success ? 'OK' : 'failed'}"
}
