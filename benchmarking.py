import argparse
import sys
import numpy as np
from fwdpy11_arg_example.evolve_arg import evolve_track
import fwdpy11 as fp11
import fwdpy11.fitness
import fwdpy11.model_params
import fwdpy11.wright_fisher as wf
import fwdpy11.sampling
import msprime
import gzip
import pandas as pd

def parse_args():
    dstring = "Prototype implementation of ARG tracking and regular garbage collection."
    parser = argparse.ArgumentParser(description=dstring,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--popsize', '-N', type=int,
                        help="Diploid population size")
    parser.add_argument('--theta', '-T', type=float,  help="4Nu")
    parser.add_argument('--rho', '-R', type=float,  help="4Nr")
    parser.add_argument('--pdel',  default=0.0, type=float,
                        help="Ratio of deleterious mutations to neutral mutations.")

    parser.add_argument('--nsam', '-n', type=int,
                        help="Sample size (in chromosomes).")
    parser.add_argument('--seed', '-S', type=int,  help="RNG seed")
    parser.add_argument('--gc', '-G', type=int,
                        help="GC interval")
    parser.add_argument('--neutral', action='store_true',
                        help="Simulate no selection")
    parser.add_argument('--neutral_mutations',
                        action='store_true',
                        help="Simulate neutral mutations.  If False, ARG is tracked instead and neutral mutations dropped down on the sample afterwards.")
    parser.add_argument('--outfile1', type=str, help="Main output file")
    parser.add_argument("--treefile","-t", type=str, dest="treefile",
                        help="name of output file for trees (default: not output)",default=None)
    return parser


if __name__ == "__main__":
    parser = parse_args()
    args = parser.parse_args(sys.argv[1:])

    pop = fp11.SlocusPop(args.popsize)

    # Set up parameters with defaults
    recrate = args.rho / (4.0 * float(args.popsize))
    mutrate_n = args.theta / (4.0 * float(args.popsize))
    mutrate_s = args.pdel * mutrate_n

    pdict = {'rates': (mutrate_n, mutrate_s, recrate),
             'nregions': [fp11.Region(0, 1, 1)],
             # The below is equivelent to R's -1*rgamma(1,shape=1.0,scale=5.0)
             # The scaling of 2N means that the DFE is with respect to 2Ns
             'sregions': [fp11.GammaS(0, 1, 1, h=0.5, mean=-5.0, shape=1.0, scaling=2 * args.popsize)],
             'recregions': [fp11.Region(0, 1, 1)],
             'gvalue': fwdpy11.fitness.SlocusMult(1.0),
             'demography': np.array([args.popsize] * 20 * args.popsize, dtype=np.uint32)
             }

    params = fwdpy11.model_params.SlocusParams(**pdict)

    # Adjust params based on user input
    if args.neutral is True:
        params.mutrate_s = 0.0
        params.sregions = []

    if args.neutral_mutations is False:
        params.mutrate_n = 0.0
        params.nregions = []

    # Run the sim.
    # If tracking the ARG, we use this current module.
    # If simulating the neutral mutations, we use
    # the regular fwdpy11 machinery.

    rng = fp11.GSLrng(args.seed)
    if args.neutral_mutations is True:
        # Use fwdpy11
        wf.evolve(rng, pop, params)
        # Get a sample
        s = fwdpy11.sampling.sample_separate(rng, pop, args.nsam)
    else:
        # Use this module
        simplifier, atracker, tsim = evolve_track(
            rng, pop, params, args.gc)
        # Take times from simplifier before they change.
        times = simplifier.times
        times['fwd_sim_runtime'] = [tsim]
        times['N'] = [args.popsize]
        times['theta'] = [args.theta]
        times['rho'] = [args.rho]
        times['simplify_interval'] = [args.gc]
        d = pd.DataFrame(times)
        d.to_csv(args.outfile1,sep='\t',index=False,compression='gzip')
        # Simplify the genealogy down to a sample,
        # And throw mutations onto that sample
        msprime.simplify_tables(np.random.choice(2 * args.popsize, args.nsam,
                                                 replace=False).tolist(),
                                nodes=simplifier.nodes,
                                edges=simplifier.edges)
        if args.treefile is not None:
            sites = msprime.SiteTable()
            mutations = msprime.MutationTable()
            ts = msprime.load_tables(nodes=simplifier.nodes,
                                     edges=simplifier.edges, sites=sites,
                                     mutations=mutations)
            ts.dump(args.treefile)
        msp_rng = msprime.RandomGenerator(args.seed)
        sites = msprime.SiteTable()
        mutations = msprime.MutationTable()
        mutgen = msprime.MutationGenerator(
            msp_rng, args.theta / float(4 * args.popsize))
        mutgen.generate(simplifier.nodes,
                        simplifier.edges, sites, mutations)
